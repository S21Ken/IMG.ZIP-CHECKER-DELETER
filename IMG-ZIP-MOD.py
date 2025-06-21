import os
import zipfile
import shutil
from PIL import Image
import streamlit as st

def get_expected_size(folder_name):
    try:
        w, h = folder_name.lower().split('x')
        return int(w), int(h)
    except ValueError:
        return None

def is_within_tolerance(actual_size, expected_size, tolerance=1):
    return (
        abs(actual_size[0] - expected_size[0]) <= tolerance and
        abs(actual_size[1] - expected_size[1]) <= tolerance
    )

def extract_zip(zip_file, extract_to):
    if os.path.exists(extract_to):
        shutil.rmtree(extract_to)
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def list_files_not_in_txt(base_dir, retain_list):
    found_names = set()
    for root, _, files in os.walk(base_dir):
        for file in files:
            name, _ = os.path.splitext(file)
            found_names.add(name)
    not_in_list = found_names - retain_list
    not_in_zip = retain_list - found_names
    return not_in_list, not_in_zip

def delete_unlisted_images(base_dir, retain_list):
    deleted = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            name, _ = os.path.splitext(file)
            if name not in retain_list:
                os.remove(os.path.join(root, file))
                deleted.append(file)
    return deleted

def check_and_delete_by_size(base_dir, tolerance):
    deleted_by_size = []
    for root, _, files in os.walk(base_dir):
        folder_name = os.path.relpath(root, base_dir).split(os.sep)[0]
        expected_size = get_expected_size(folder_name)
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with Image.open(file_path) as img:
                    actual_size = img.size
                if expected_size and not is_within_tolerance(actual_size, expected_size, tolerance):
                    os.remove(file_path)
                    deleted_by_size.append(f"{file} | Expected: {expected_size}, Actual: {actual_size}")
            except Exception as e:
                st.warning(f"Could not open {file_path}: {e}")
    return deleted_by_size

def create_zip_from_folder(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                abs_path = os.path.join(root, file)
                arcname = os.path.relpath(abs_path, folder_path)
                zipf.write(abs_path, arcname)

def main():
    st.set_page_config(page_title="Image Cleaner", layout="centered")
    st.title("🖼️ Clean Image ZIP by List & Size")

    # Invisible watermark
    st.markdown("""
        <style>
            .hidden-kms {
                color: transparent;
                user-select: text;
                font-size: 1px;
                line-height: 0;
            }
            .hidden-kms::selection {
                background: yellow;
                color: black;
            }
        </style>
        <div class="hidden-kms">KMS</div>
    """, unsafe_allow_html=True)

    uploaded_zip = st.file_uploader("📦 Upload ZIP File", type=["zip"])
    uploaded_txt = st.file_uploader("📄 Upload List (TXT)", type=["txt"])
    tolerance = st.slider("📏 Size Tolerance (±px)", min_value=0, max_value=10, step=1, value=1)




    if uploaded_zip and uploaded_txt:
        zip_path = "temp_input.zip"
        txt_path = "temp_list.txt"
        extract_path = "temp_extracted"

        with open(zip_path, 'wb') as f:
            f.write(uploaded_zip.read())
        with open(txt_path, 'wb') as f:
            f.write(uploaded_txt.read())

        with open(txt_path, 'r') as f:
            retain_list = {line.strip() for line in f if line.strip()}

        extract_zip(zip_path, extract_path)

        not_in_list, not_in_zip = list_files_not_in_txt(extract_path, retain_list)

        st.subheader("🔍 Image Validation Summary")
        st.success(f"✔️ Total in list: {len(retain_list)}")
        st.warning(f"⚠️ Found {len(not_in_list)} image(s) not in the list")
        st.warning(f"⚠️ {len(not_in_zip)} listed name(s) not found in ZIP")

        with st.expander("🗂️ Show image names NOT in list"):
            st.code("\n".join(sorted(not_in_list)), language='text')

        with st.expander("🗂️ Show list names NOT in ZIP"):
            st.code("\n".join(sorted(not_in_zip)), language='text')

        if st.button("🧹 Delete images NOT in list"):

            deleted = delete_unlisted_images(extract_path, retain_list)
            st.success(f"🗑️ Deleted {len(deleted)} images not in the list.")

        if st.button("📐 Delete images with incorrect size"):
            deleted_by_size = check_and_delete_by_size(extract_path, tolerance)
            st.success(f"🗑️ Deleted {len(deleted_by_size)} images with size mismatch.")
            with st.expander("📄 Deleted size mismatch details"):
                st.code("\n".join(deleted_by_size))

        if st.button("🧹 Clean All (Not in List + Incorrect Size)"):
            deleted = delete_unlisted_images(extract_path, retain_list)
            deleted_by_size = check_and_delete_by_size(extract_path, tolerance)

            st.success(f"🧹 Cleaned {len(deleted)} images not in list and {len(deleted_by_size)} size mismatches.")
            with st.expander("📄 Deleted by size mismatch (from Clean All)"):
                st.code("\n".join(deleted_by_size))


        result_zip = "filtered_output.zip"
        create_zip_from_folder(extract_path, result_zip)

        with open(result_zip, "rb") as f:
            st.download_button(
                label="⬇️ Download Cleaned ZIP",
                data=f,
                file_name="filtered_images.zip",
                mime="application/zip"
            )

if __name__ == "__main__":
    main()
