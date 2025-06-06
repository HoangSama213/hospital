import streamlit as st
import pandas as pd
import datetime
import os # Import os để kiểm tra sự tồn tại của file

# --- Cấu hình trang Streamlit ---
# st.set_page_config() phải là lệnh Streamlit đầu tiên trong script
st.set_page_config(
    page_title="Quản lý Bệnh viện ITC",
    layout="centered", # hoặc "wide"
    initial_sidebar_state="auto"
)


# Đường dẫn đến file lưu trữ dữ liệu bệnh viện
path = 'BV.txt' # Đặt file trong cùng thư mục với script Streamlit để dễ quản lý
disease_data_path = 'du_lieu_benh.txt' # Đường dẫn đến file dữ liệu bệnh

# --- Hàm xử lý file ---
# Hàm lưu dữ liệu bệnh nhân vào file
def save_patients_to_file(patients_list):
    """Ghi toàn bộ danh sách bệnh nhân vào file, ghi đè nội dung cũ."""
    try:
        with open(path, 'w', encoding='utf8') as f:
            for benh_nhan_info in patients_list:
                # Đảm bảo mỗi bệnh nhân là một list/tuple trước khi join
                if isinstance(benh_nhan_info, list):
                    f.write('-'.join(benh_nhan_info) + '\n')
                else:
                    # Xử lý trường hợp dữ liệu không phải là list (ví dụ: từ DataFrame)
                    # Chuyển đổi về list string trước khi join
                    f.write('-'.join(map(str, benh_nhan_info)) + '\n')
        st.success("Dữ liệu đã được lưu thành công vào file.")
    except Exception as e:
        st.error(f"Lỗi khi lưu dữ liệu vào file: {e}")

# Hàm đọc dữ liệu bệnh nhân từ file
def read_patients_from_file():
    """Đọc dữ liệu bệnh nhân từ file và trả về danh sách các list."""
    bn = []
    if not os.path.exists(path):
        # Tạo file nếu nó không tồn tại
        try:
            with open(path, 'w', encoding='utf8') as f:
                pass # Tạo file rỗng
            st.info(f"File '{path}' không tồn tại, đã tạo file mới.")
        except Exception as e:
            st.error(f"Không thể tạo file '{path}': {e}")
            return [] # Trả về list rỗng nếu không tạo được file
        return []

    try:
        with open(path, 'r', encoding='utf8') as f:
            for i in f:
                data = i.strip()
                if data: # Đảm bảo dòng không rỗng
                    arr = data.split('-')
                    # Đảm bảo có đủ 5 phần dữ liệu
                    if len(arr) == 5:
                        bn.append([part.strip() for part in arr])
                    else:
                        st.warning(f"Dòng dữ liệu không hợp lệ (không đủ 5 phần): {data}")
    except FileNotFoundError: # Mặc dù đã kiểm tra os.path.exists, vẫn giữ để an toàn
        st.error(f"Lỗi: Không tìm thấy file '{path}'.")
        return []
    except Exception as e:
        st.error(f"Lỗi khi đọc file '{path}': {e}")
        return []
    return bn

# --- Hàm đọc dữ liệu bệnh và mức độ khẩn cấp từ du_lieu_benh.txt ---
@st.cache_data # Cache dữ liệu bệnh để chỉ đọc một lần
def load_disease_data(file_path):
    """Đọc dữ liệu bệnh từ file và trả về từ điển {tên bệnh: mức độ khẩn cấp (số)}.
    Mức độ khẩn cấp trong file là số (0-4).
    """
    disease_map = {}
    if not os.path.exists(file_path):
        st.error(f"Lỗi: Không tìm thấy file dữ liệu bệnh '{file_path}'. Vui lòng đảm bảo file tồn tại.")
        return {}
    try:
        with open(file_path, 'r', encoding='utf8') as f:
            # Bỏ qua dòng tiêu đề
            next(f) 
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 2:
                    disease_name = parts[0].strip()
                    emergency_level = int(parts[1].strip()) # Chuyển đổi sang số nguyên
                    disease_map[disease_name.lower()] = emergency_level # Lưu tên bệnh dưới dạng chữ thường để dễ tra cứu
                else:
                    st.warning(f"Dòng dữ liệu bệnh không hợp lệ: {line.strip()}")
    except Exception as e:
        st.error(f"Lỗi khi đọc file dữ liệu bệnh '{file_path}': {e}")
    return disease_map

# Ánh xạ mức độ khẩn cấp từ số sang chuỗi mô tả
EMERGENCY_LEVEL_MAP = {
    0: "khẩn cấp",
    1: "nghiêm trọng",
    2: "trung bình",
    3: "nhẹ",
    4: "nhẹ" # Gộp 3 và 4 vào "nhẹ"
}

# Tải dữ liệu bệnh khi ứng dụng khởi động
DISEASE_DATA = load_disease_data(disease_data_path)

# --- Khởi tạo trạng thái phiên (session state) ---
# Tải dữ liệu khi ứng dụng khởi động lần đầu
if 'patients' not in st.session_state:
    st.session_state.patients = read_patients_from_file()
if 'show_detail' not in st.session_state:
    st.session_state.show_detail = False
if 'selected_patient_index' not in st.session_state:
    st.session_state.selected_patient_index = -1
if 'confirm_delete_index' not in st.session_state: # Thêm trạng thái xác nhận xóa
    st.session_state.confirm_delete_index = -1 # Lưu index của bệnh nhân cần xác nhận xóa

# --- Hàm thêm bệnh nhân ---
def add_patient(name, age, sex, disease_name, time_str):
    """Thêm bệnh nhân mới vào danh sách và lưu vào file.
    Tình trạng khẩn cấp được xác định tự động từ tên bệnh.
    """
    if not all([name, age, sex, disease_name, time_str]):
        st.error("Vui lòng điền đầy đủ tất cả các trường thông tin.")
        return

    # Kiểm tra tuổi và thời gian có hợp lệ không
    try:
        int(age)
    except ValueError:
        st.error("Tuổi phải là một số nguyên.")
        return
    
    try:
        # Kiểm tra định dạng thời gian HH:MM
        datetime.datetime.strptime(time_str, "%H:%M")
    except ValueError:
        st.error("Thời gian đến không hợp lệ. Vui lòng nhập theo định dạng HH:MM.")
        return

    # Xác định tình trạng khẩn cấp từ tên bệnh
    emergency_level_num = DISEASE_DATA.get(disease_name.lower()) # Tra cứu mức độ khẩn cấp bằng tên bệnh (chữ thường)
    
    if emergency_level_num is not None:
        condition = EMERGENCY_LEVEL_MAP.get(emergency_level_num, "nhẹ") # Mặc định là "nhẹ" nếu mức độ không xác định
        st.info(f"Tên bệnh '{disease_name}' được xác định là: **{condition}**.")
    else:
        condition = "nhẹ" # Mặc định là "nhẹ" nếu không tìm thấy bệnh
        st.warning(f"Không tìm thấy bệnh '{disease_name}' trong dữ liệu. Tình trạng mặc định là **{condition}**.")

    new_patient = [name, age, sex, condition, time_str] # Sử dụng condition đã xác định
    st.session_state.patients.append(new_patient)
    save_patients_to_file(st.session_state.patients)
    st.success(f"Đã thêm bệnh nhân '{name}' thành công!")
    # Xóa nội dung các trường nhập liệu sau khi thêm
    st.session_state.input_name = ""
    st.session_state.input_age = 0
    st.session_state.input_sex = ""
    st.session_state.input_disease_name = "" # Reset trường tên bệnh
    st.session_state.input_hour = 0
    st.session_state.input_minute = 0
    st.session_state.confirm_delete_index = -1 # Đảm bảo reset trạng thái xóa
    st.rerun() # Chạy lại để cập nhật giao diện

# --- Hàm sắp xếp bệnh nhân ---
def sort_patients():
    """Sắp xếp danh sách bệnh nhân theo tình trạng và thời gian đến."""
    if not st.session_state.patients:
        st.info("Không có bệnh nhân để sắp xếp.")
        return

    # Định nghĩa thứ tự ưu tiên của tình trạng (đã được ánh xạ từ số)
    # Giá trị số càng nhỏ, ưu tiên càng cao
    tinh_trang_priority = {
        "khẩn cấp": 1,
        "nghiêm trọng": 2,
        "trung bình": 3,
        "nhẹ": 4
    }

    def get_sort_key(patient_data):
        # patient_data là một list: [tên, tuổi, giới tính, tình trạng, thời gian]
        condition = patient_data[3].strip().lower()
        time_str = patient_data[4].strip()

        # Lấy ưu tiên tình trạng, nếu không có trong dict thì đặt ưu tiên thấp nhất (số lớn)
        priority = tinh_trang_priority.get(condition, 99)

        # Chuyển đổi thời gian sang đối tượng datetime để so sánh
        try:
            time_obj = datetime.datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            # Xử lý trường hợp thời gian không hợp lệ, đặt nó xuống cuối
            time_obj = datetime.time(23, 59) # Thời gian cuối cùng trong ngày

        return (priority, time_obj)

    st.session_state.patients.sort(key=get_sort_key)
    save_patients_to_file(st.session_state.patients) # Lưu lại sau khi sắp xếp
    st.success("Đã sắp xếp danh sách bệnh nhân.")
    # Reset radio button và chi tiết sau khi sắp xếp
    if 'selected_patient_radio' in st.session_state:
        del st.session_state.selected_patient_radio
    st.session_state.show_detail = False
    st.session_state.confirm_delete_index = -1 # Đảm bảo reset trạng thái xóa
    st.rerun()

# --- Hàm xóa bệnh nhân ---
def delete_patient(index_to_delete):
    """Xóa bệnh nhân khỏi danh sách theo chỉ mục và lưu vào file."""
    if 0 <= index_to_delete < len(st.session_state.patients):
        deleted_patient = st.session_state.patients.pop(index_to_delete)
        save_patients_to_file(st.session_state.patients)
        st.success(f"Đã xóa bệnh nhân '{deleted_patient[0]}' thành công.")
        # Reset radio button và chi tiết sau khi xóa
        if 'selected_patient_radio' in st.session_state:
            del st.session_state.selected_patient_radio
        st.session_state.show_detail = False
        st.session_state.confirm_delete_index = -1 # Rất quan trọng: Reset trạng thái xác nhận
        st.rerun()
    else:
        st.error("Không tìm thấy bệnh nhân để xóa.")

# --- Tiêu đề ứng dụng ---
st.title('🏥 Quản lý Bệnh viện ITC')

# --- Hiển thị danh sách bệnh nhân ---
st.subheader("Danh sách Bệnh nhân")

if st.session_state.patients:
    # Tạo DataFrame từ danh sách bệnh nhân để hiển thị
    df_patients = pd.DataFrame(st.session_state.patients, columns=[
        "Họ và tên", "Tuổi", "Giới tính", "Tình trạng", "Thời gian đến"
    ])

    # Hiển thị DataFrame
    st.dataframe(
        df_patients,
        use_container_width=True,
        hide_index=True, # Ẩn chỉ mục mặc định của DataFrame
        column_order=["Họ và tên", "Tuổi", "Giới tính", "Tình trạng", "Thời gian đến"]
    )

    # Tạo một list các chuỗi để hiển thị trong st.radio
    patient_display_list = [f"{idx + 1}. {' - '.join(p)}" for idx, p in enumerate(st.session_state.patients)]
    
    st.markdown("---")
    st.subheader("Chọn bệnh nhân để xem chi tiết hoặc xóa")
    
    selected_patient_display = st.radio(
        "Chọn bệnh nhân:",
        patient_display_list,
        index=None, # Không chọn gì ban đầu
        key="selected_patient_radio"
    )

    selected_index_for_action = -1
    if selected_patient_display:
        # Trích xuất chỉ mục từ chuỗi hiển thị
        try:
            selected_index_for_action = int(selected_patient_display.split('.')[0]) - 1
        except ValueError:
            st.error("Lỗi khi xác định bệnh nhân được chọn.")

    # --- Các nút thao tác với danh sách ---
    col_view, col_delete, col_sort, col_reload = st.columns(4)

    with col_view:
        if st.button("Xem chi tiết", key="btn_view_detail"):
            if selected_index_for_action != -1:
                st.session_state.selected_patient_index = selected_index_for_action
                st.session_state.show_detail = True
                st.session_state.confirm_delete_index = -1 # Reset trạng thái xác nhận xóa
                st.rerun() # Chạy lại để hiển thị chi tiết
            else:
                st.warning("Vui lòng chọn một bệnh nhân để xem chi tiết.")

    with col_delete:
        if st.button("Xóa bệnh nhân", key="btn_delete_patient"):
            if selected_index_for_action != -1:
                # Lưu chỉ mục cần xóa vào session_state để xác nhận
                st.session_state.confirm_delete_index = selected_index_for_action
                st.rerun() # Chạy lại để hiển thị nút xác nhận
            else:
                st.warning("Vui lòng chọn một bệnh nhân để xóa.")
    
    # Hiển thị nút xác nhận xóa nếu có bệnh nhân đang chờ xác nhận
    if st.session_state.confirm_delete_index != -1:
        patient_to_confirm_delete = st.session_state.patients[st.session_state.confirm_delete_index][0]
        st.warning(f"Bạn có chắc chắn muốn xóa bệnh nhân '{patient_to_confirm_delete}' không?")
        
        col_confirm_del, col_cancel_del = st.columns(2)
        with col_confirm_del:
            if st.button("Xác nhận Xóa", key="confirm_delete_btn"):
                delete_patient(st.session_state.confirm_delete_index) # Gọi hàm xóa
        with col_cancel_del:
            if st.button("Hủy", key="cancel_delete_btn"):
                st.session_state.confirm_delete_index = -1 # Hủy xác nhận
                st.rerun() # Chạy lại để ẩn nút xác nhận

    with col_sort:
        if st.button("Sắp xếp bệnh nhân", key="btn_sort_patients"):
            sort_patients()
        
    with col_reload: # Nút tải lại dữ liệu từ file
        if st.button("Tải lại dữ liệu từ File", key="btn_reload_data"):
            st.session_state.patients = read_patients_from_file()
            st.info("Đã tải lại dữ liệu từ file.")
            # Reset radio button và chi tiết sau khi tải lại
            if 'selected_patient_radio' in st.session_state:
                del st.session_state.selected_patient_radio
            st.session_state.show_detail = False
            st.session_state.confirm_delete_index = -1 # Đảm bảo reset trạng thái xóa
            st.rerun()

else:
    st.info("Chưa có bệnh nhân nào trong danh sách.")

# --- Hiển thị thông tin chi tiết (nếu có) ---
if 'show_detail' in st.session_state and st.session_state.show_detail:
    if 'selected_patient_index' in st.session_state and st.session_state.selected_patient_index != -1:
        patient_info = st.session_state.patients[st.session_state.selected_patient_index]
        st.markdown("---")
        st.subheader("Thông tin chi tiết bệnh nhân")
        
        if len(patient_info) >= 5:
            st.write(f"**Họ và tên:** {patient_info[0]}")
            st.write(f"**Tuổi:** {patient_info[1]}")
            st.write(f"**Giới tính:** {patient_info[2]}")
            st.write(f"**Tình trạng:** {patient_info[3]}")
            st.write(f"**Thời gian đến:** {patient_info[4]}")
        else:
            st.warning("Dữ liệu bệnh nhân không hợp lệ để hiển thị chi tiết.")
        
        if st.button("Đóng thông tin chi tiết", key="close_detail"):
            st.session_state.show_detail = False
            st.session_state.selected_patient_index = -1
            st.session_state.confirm_delete_index = -1 # Đảm bảo reset trạng thái xóa
            st.rerun() 

# --- Form thêm bệnh nhân mới ---
st.markdown("---")
st.subheader("Thêm Bệnh nhân mới")

# Khởi tạo giá trị mặc định cho các input nếu chưa có trong session_state
if 'input_name' not in st.session_state: st.session_state.input_name = ""
if 'input_age' not in st.session_state: st.session_state.input_age = 0 # Đặt mặc định là 0 cho number_input
if 'input_sex' not in st.session_state: st.session_state.input_sex = ""
if 'input_disease_name' not in st.session_state: st.session_state.input_disease_name = "" # Thêm trạng thái cho tên bệnh
if 'input_hour' not in st.session_state: st.session_state.input_hour = 0
if 'input_minute' not in st.session_state: st.session_state.input_minute = 0


with st.form("add_patient_form", clear_on_submit=False): # Giữ lại giá trị sau khi submit
    name_input = st.text_input("Họ và tên bệnh nhân:", value=st.session_state.input_name, key="form_name")
    age_input = st.number_input("Tuổi:", min_value=0, max_value=150, value=int(st.session_state.input_age), key="form_age")
    sex_input = st.text_input("Giới tính:", value=st.session_state.input_sex, key="form_sex")
    
    # Thêm trường nhập tên bệnh, loại bỏ selectbox Tình trạng
    disease_name_input = st.text_input("Tên bệnh:", value=st.session_state.input_disease_name, key="form_disease_name")

    st.write("Thời gian đến (HH:MM):")
    col_hour, col_minute = st.columns(2)
    with col_hour:
        hour_input = st.number_input("Giờ:", min_value=0, max_value=23, format="%02d", value=st.session_state.input_hour, key="form_hour")
    with col_minute:
        minute_input = st.number_input("Phút:", min_value=0, max_value=59, format="%02d", value=st.session_state.input_minute, key="form_minute")

    # Nút submit form
    submitted = st.form_submit_button("Thêm Bệnh nhân")
    if submitted:
        time_str = f"{hour_input:02d}:{minute_input:02d}"
        # Truyền thêm disease_name_input vào hàm add_patient
        add_patient(name_input, str(age_input), sex_input, disease_name_input, time_str)
        # Cập nhật lại các giá trị input trong session_state để xóa chúng trên giao diện
        st.session_state.input_name = ""
        st.session_state.input_age = 0
        st.session_state.input_sex = ""
        st.session_state.input_disease_name = "" # Reset trường tên bệnh
        st.session_state.input_hour = 0
        st.session_state.input_minute = 0
        st.rerun() # Chạy lại toàn bộ script để cập nhật danh sách và xóa form

# Footer
st.markdown("---")
st.markdown("Ứng dụng Quản lý Bệnh viện ITC - Được xây dựng bằng Streamlit")
