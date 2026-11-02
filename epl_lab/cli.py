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
        print('\nNGOẠI HẠNG ANH 2025–2026 — DỮ LIỆU THẬT\n1. Bảng điểm\n2. Tìm đội và lịch sử trận\n3. Phong độ 5 trận\n4. So sánh 2 đội\n5. Nguồn và chất lượng\n6. Xuất báo cáo\n0. Thoát')
        choice=input('Chọn số: ').strip()
        if choice=='0':return
        try:
            if choice=='5':
                show(quality(a.db))
                from .download import URL,SHA256
                print(URL,'\nSHA256:',SHA256);continue
            if choice not in ['1','2','3','4','6']:print('Nhập số từ 0 đến 6.');continue
            as_of=input('Mốc YYYY-MM-DD (Enter: hết mùa): ').strip() or None
            if choice=='6':print(analyze(a.db,as_of));continue
            tables=queries(a.db,as_of)
            if choice=='1':show(tables['standings']);print('Điểm từ tỷ số; chưa xét điều chỉnh hành chính/đối đầu.');continue
            if choice=='3':show(tables['last5_form']);continue
            name=choose_team(a.db)
            if name is None:continue
            if choice=='2':show(tables['team_matches'].loc[lambda d:d.name==name,['played_on','venue','name','opponent','gf','ga','outcome','points']])
            else:
                other=choose_team(a.db)
                if other==name:raise ValueError('Hãy chọn hai đội khác nhau')
                show(tables['standings'][tables['standings'].name.isin([name,other])]);show(tables['home_away'][tables['home_away'].name.isin([name,other])])
        except (ValueError,OSError) as exc:print('Chưa thực hiện được:',exc)
if __name__=='__main__':main()
