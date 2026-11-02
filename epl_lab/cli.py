import argparse
from .db import DEFAULT_DB,connect
from .analysis import queries,quality
from .analyze import analyze
def show(df):
    if df.empty:print('Không có kết quả.');return
    for start in range(0,len(df),20):
        print(df.iloc[start:start+20].to_string(index=False))
        if start+20<len(df) and input('Enter: trang sau; q: dừng > ').strip().lower()=='q':break
def choose_team(db):
    with connect(db) as c:rows=c.execute('SELECT team_id,name FROM teams ORDER BY name').fetchall()
    word=input('Tên đội (Enter để liệt kê tất cả): ').strip()
    found=[r for r in rows if word.casefold() in r[1].casefold()]
    if not found:print('Không tìm thấy đội.');return None
    for i,(_,name) in enumerate(found,1):print(f'{i}. {name}')
    value=int(input('Chọn số trong danh sách: '))
    if not 1<=value<=len(found):raise ValueError('Chọn số trong danh sách đang hiển thị')
    return found[value-1][1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default=str(DEFAULT_DB));a=p.parse_args()
    quality(a.db)
    while True:
        print('\nNGOẠI HẠNG ANH 2025–2026 — DỮ LIỆU THẬT\n1. Bảng điểm và kiểm soát bóng trung bình\n2. Tìm đội và lịch sử trận\n3. Phong độ 5 trận\n4. So sánh 2 đội\n5. Nguồn và chất lượng\n6. Xuất báo cáo\n7. Tải/bổ sung dữ liệu kiểm soát bóng\n8. Bảng kiểm soát bóng trung bình dễ đọc\n0. Thoát')
        choice=input('Chọn số: ').strip()
        if choice=='0':return
        try:
            if choice=='7':
                from .possession import install
                print('Tải dữ liệu thật FPL Core Insights (cần mạng lần đầu), kiểm tra SHA256 và đối chiếu trận...')
                print(install(a.db));continue
            if choice=='5':
                show(quality(a.db))
                from .download import URL,SHA256
                print(URL,'\nSHA256:',SHA256);continue
            if choice not in ['1','2','3','4','6','8']:print('Nhập số từ 0 đến 8.');continue
            as_of=input('Mốc YYYY-MM-DD (Enter: hết mùa): ').strip() or None
            if choice=='6':print(analyze(a.db,as_of));continue
            tables=queries(a.db,as_of)
            if choice=='8':
                summary=tables['standings'][['name','played','avg_possession_pct','possession_matches','possession_missing']].sort_values('avg_possession_pct',ascending=False,na_position='last')
                show(summary.rename(columns={'name':'Đội','played':'Đã đá','avg_possession_pct':'TB (%)','possession_matches':'Có dữ liệu','possession_missing':'Thiếu/xung đột'}).round(2).fillna('Chưa có'))
                print('TB cộng theo các trận hợp lệ đến mốc. Thiếu/xung đột không tính thành 0%. Chưa tải dữ liệu thì chọn 7.');continue
            if choice=='1':
                show(tables['standings'].round({'avg_possession_pct':2}))
                print('avg_possession_pct: kiểm soát bóng TB (%); possession_matches: số trận dùng tính TB; possession_missing: số trận chưa đủ tin cậy. Trống không phải 0%. Chọn 7 nếu chưa tải dữ liệu.')
                print('Điểm từ tỷ số; chưa xét điều chỉnh hành chính/đối đầu.');continue
            if choice=='3':show(tables['last5_form']);continue
            name=choose_team(a.db)
            if name is None:continue
            if choice=='2':show(tables['team_matches'].loc[lambda d:d.name==name,['played_on','venue','name','opponent','gf','ga','outcome','points','possession_pct']])
            else:
                other=choose_team(a.db)
                if other==name:raise ValueError('Hãy chọn hai đội khác nhau')
                show(tables['standings'][tables['standings'].name.isin([name,other])].round({'avg_possession_pct':2}));show(tables['home_away'][tables['home_away'].name.isin([name,other])].round({'avg_possession_pct':2}))
        except (ValueError,OSError) as exc:print('Chưa thực hiện được:',exc)
if __name__=='__main__':main()
