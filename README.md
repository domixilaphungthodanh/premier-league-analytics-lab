# Premier League Analytics Lab ⚽

Học SQL qua **dữ liệu thật toàn bộ Ngoại hạng Anh 2025–2026**. Python 3.12 · SQLite · pandas · Seaborn · Matplotlib · Jupyter.

## Chạy bằng PowerShell — bắt đầu ở đây

1. Tải ZIP tại [Releases](https://github.com/domixilaphungthodanh/premier-league-analytics-lab/releases/latest), giải nén toàn bộ.
2. Mở thư mục vừa giải nén trong File Explorer. Gõ `powershell` vào thanh địa chỉ rồi Enter. **Không chạy từ system32 hoặc thư mục người dùng.**
3. Kiểm tra và chạy:

```powershell
Get-Location
Get-ChildItem
python --version
python src/prepare_data.py
python src/analyze.py
python run_premier.py --notebook
```

Bạn phải thấy `run_premier.py`, `src`, `requirements.txt` ở bước kiểm tra. Python cần phiên bản **3.12**. Lần đầu cần mạng cài thư viện và tải CSV; các lần sau có thể học offline khi đã có DB và thư viện Notebook. Không cần Git. Có thêm `START_WINDOWS.cmd` và `START_NOTEBOOK.cmd` để nhấp đúp. Đây chưa phải EXE độc lập. Đường dẫn có dấu/khoảng trắng được hỗ trợ; launcher dùng môi trường ngắn nếu đường dẫn Windows quá sâu. Không tắt chính sách bảo mật Windows.

Trong Jupyter mở **`notebooks/02_analysis.ipynb`**, Shift+Enter từng ô. SQL nằm trong chuỗi Python `read_sql("SELECT ...")`, không gõ SQL trực tiếp vào PowerShell. Menu chỉ nhận số:

```powershell
python run_premier.py
```

`cd "đường dẫn thư mục"` để đổi thư mục; `Get-Location` xem vị trí; `Get-ChildItem` xem file. PowerShell không dùng `cd /d`.

## Nguồn và độ đầy đủ

- [Football-Data: England](https://football-data.co.uk/englandm.php), [CSV mùa 2526/E0](https://football-data.co.uk/mmz4281/2526/E0.csv), [giải thích trường](https://football-data.co.uk/notes.txt).
- Snapshot kiểm tra ngày **02/11/2026**, **380 trận, 20 đội**, mỗi đội **19 trận sân nhà + 19 sân khách**, từ **15/08/2025 đến 24/05/2026**.
- SHA256: `3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62`.
- Chốt nội dung bằng SHA256 vì URL nguồn có thể được cập nhật. Nếu nguồn thay đổi, dừng và yêu cầu kiểm tra phiên bản mới; không tự sửa checksum hoặc đổi nguồn.
- Có manifest URL/thời gian lấy/kích thước/hash; từng trận giữ số dòng CSV nguồn. File tải đầy đủ có cột tỷ lệ cược, **chương trình không nhập hoặc phân tích các cột đó**.
- Mã MIT; dữ liệu bên thứ ba theo điều kiện của nguồn, không tự gán MIT cho dữ liệu. Repo/ZIP không đóng gói CSV thật. Ghi nguồn khi chia sẻ kết quả; kiểm tra điều kiện nguồn trước khi tái phân phối dữ liệu.

Tải trực tiếp nguồn, không cần tài khoản/API key/Kaggle. Nếu tải tự động lỗi, tải thủ công đúng CSV trên rồi:

```powershell
python src/prepare_data.py --input "C:\Users\Dell XPS\Downloads\E0.csv"
```

CSV chỉ được nhập nếu hash và kiểm tra toàn mùa đều đúng. Không tự bỏ dòng sai hoặc thay dữ liệu giả lập.

## Bạn sẽ nhận được gì?

- Bảng điểm, W/D/L, bàn thắng/thua, hiệu số, điểm; lịch sử theo đội và so sánh hai đội.
- Sân nhà/sân khách, tối đa năm trận gần nhất tại mốc.
- **4 PNG**: điểm theo đội, điểm sân nhà/sân khách, bàn thắng theo tháng, cú sút so với bàn thắng.
- **6 CSV**: standings, team_matches, home_away, last5_form, monthly, data_quality; báo cáo Markdown ba nhận xét.
- SQL và pandas tính độc lập, phải khớp trước khi xuất.

**Bảng điểm học tập từ tỷ số:** thắng 3, hòa 1, thua 0. Xếp theo điểm, hiệu số, bàn thắng; nếu cùng cả ba thì cùng hạng, tên chỉ giúp hiển thị ổn định. Chưa có trừ điểm hành chính hoặc quyết định đối đầu/play-off khi quyền lợi chính thức cần phân định. Xem [quy định giải](https://www.premierleague.com/en/news/58905). Không gọi đây là bảng chính thức đã xử lý mọi quyết định ngoài sân.

Mốc `--as-of` là **hết ngày theo ngày nguồn**, không phải trạng thái trực tiếp theo giờ Việt Nam. Không suy vòng đấu từ ngày hoặc thứ tự CSV vì có đá bù. Phong độ lấy trận thực tế gần nhất, không cố định vòng. Không có cầu thủ, xG hoặc phút thi đấu. Thống kê thiếu giữ NULL, không giả thành 0. Chỉ mô tả một mùa, không khẳng định nguyên nhân hoặc dự đoán tương lai.

```powershell
python src/analyze.py --as-of 2026-01-01 --out outputs/january
python src/prepare_data.py --db database/practice.db
python run_premier.py --notebook --db database/practice.db
```

`prepare_data.py` giữ nguyên DB có sẵn, chỉ kiểm tra và xuất CSV bảng nguồn. Import trực tiếp không ghi đè DB; tạo bản khác bằng `--db`. Dữ liệu giữa các máy không tự đồng bộ. Database, môi trường, file nguồn, báo cáo và notebook đã chạy không đưa vào Git/ZIP.

## Cấu trúc giống Sales Analysis Lab

```text
src/prepare_data.py         Tải/nhập nếu thiếu DB; xuất CSV nguồn
src/analyze.py              Đối chiếu và xuất báo cáo
data/raw/                  CSV và manifest sinh ra
database/premier.db         SQLite sinh ra
sql/schema.sql             Khóa, ràng buộc và indexes
sql/analysis.sql           Truy vấn mẫu
notebooks/02_analysis.ipynb Bài tổng hợp học trước
notebooks/lessons/         Tám buổi chuyên sâu
epl_lab/                   Hàm dùng chung
docs/                      20 bài tập, lời giải, từ điển
tests/                     Kiểm thử bằng dữ liệu nhỏ giả lập
outputs/                   Bảng, hình và báo cáo
```

## Cài thủ công / máy Linux

```powershell
python -m pip install -r requirements.txt
python -m epl_lab.download
python -m epl_lab.import_data
python -m epl_lab.cli
python -m epl_lab.analyze --as-of 2026-05-24
python -m notebook
```

`python -m` chạy module. `--db` chọn SQLite; import `--input` chọn CSV; analyze `--as-of` chọn ngày và `--out` chọn thư mục kết quả. Launcher nhận `--db`, `--notebook`, `--setup-only`. Các lệnh này chạy ở thư mục dự án. Notebook dùng kết nối chỉ đọc; bài ghi dùng SQLite tạm.

## Lộ trình học và Git

Học notebook tổng hợp trước, sau đó [tám buổi](docs/learning_path.md), [20 bài tập](docs/exercises.md), [lời giải riêng](docs/solutions.md), [từ điển và sơ đồ](docs/data_dictionary.md).

Bài mở rộng chưa triển khai: **lọc lịch sử đội theo số bàn thắng tối thiểu**. Tự tạo Issue, đặt tiêu chí, viết kiểm thử rồi sửa mã, `git diff`, `git add`, `git commit`, `git push`. Không tạo commit rỗng để tăng số lượng.

```powershell
python -m unittest discover -s tests -v
python -m epl_lab.execute_notebooks
```

Actions kiểm thử Windows/Linux với fixture ghi rõ giả lập. Workflow thủ công tải file thật đã chốt, phân tích và chạy chín notebook, lưu báo cáo/notebook 14 ngày; không đưa raw CSV vào artifact. Public repo cho phép mọi người đọc và học.
