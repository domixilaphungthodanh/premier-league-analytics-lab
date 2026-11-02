import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from .db import ROOT,DEFAULT_DB
from .analysis import reconcile,scope,quality
from .download import URL,SHA256
def analyze(db=DEFAULT_DB,as_of=None,out=None):
    as_of=scope(db,as_of);tables=reconcile(db,as_of)
    tables['data_quality']=quality(db)
    out=Path(out or ROOT/'outputs'/as_of);out.mkdir(parents=True,exist_ok=True)
    for name,df in tables.items():df.to_csv(out/(name+'.csv'),index=False,encoding='utf-8-sig')
    sns.set_theme(style='whitegrid');s=tables['standings'];tm=tables['team_matches']
    def save(filename,title,draw,empty=False):
        fig,ax=plt.subplots(figsize=(11,7))
        if empty:ax.text(.5,.5,'No matches in this date range',ha='center',transform=ax.transAxes);ax.axis('off')
        else:draw(ax)
        ax.set_title(title+' | 2025–2026 | '+as_of);fig.tight_layout();fig.savefig(out/filename,dpi=150);plt.close(fig)
    save('01_points.png','Points earned from match results',lambda ax:sns.barplot(data=s,x='points',y='name',color='#267eaa',ax=ax),not len(tm))
    v=tables['home_away']
    save('02_home_away.png','Home vs away points',lambda ax:sns.barplot(data=v,x='points',y='name',hue='venue',ax=ax),not len(tm))
    monthly=tables['monthly'].dropna(subset=['goals'])
    def trend(ax):
        sns.lineplot(data=monthly,x='month',y='goals',marker='o',ax=ax);ax.tick_params(axis='x',rotation=40);ax.set_ylabel('Goals (all completed matches)')
    save('03_monthly_goals.png','Goals by calendar month (not matchweek)',trend,not len(tm))
    def scatter(ax):
        stats=tm.groupby('name').agg(shots=('shots',lambda z:z.sum(min_count=1)),gf=('gf','sum')).dropna()
        sns.scatterplot(data=stats,x='shots',y='gf',s=70,ax=ax)
        offsets={'Leeds':(5,12),"Nott'm Forest":(-76,-1),'Fulham':(5,-10)}
        for name,r in stats.iterrows():
            dx,dy=offsets.get(name,(-6,5) if r.shots>stats.shots.max()*.95 else (4,5))
            ax.annotate(name,(r.shots,r.gf),xytext=(dx,dy),textcoords='offset points',fontsize=8,ha='right' if dx==-6 else 'left')
        ax.margins(x=.1,y=.1)
        ax.set_xlabel('Total shots (source definition)');ax.set_ylabel('Goals scored')
    save('04_shots_goals.png','Shots and goals by team',scatter,not len(tm))
    top=s.iloc[0];form=tables['last5_form'];count=len(tm)//2
    notes=[f'Đã phân tích **{count} trận** đến hết ngày **{as_of}**. Tổng bàn thắng: **{int(s.gf.sum())}**.']
    if count:
        notes.append(f'Đội đứng đầu theo điểm/hiệu số/bàn thắng: **{top["name"]}**, **{int(top.points)} điểm** sau **{int(top.played)} trận**.')
        f=form.iloc[0];notes.append(f'Trong tối đa 5 trận gần nhất, **{f["name"]}** đạt **{int(f.last5_points)} điểm / {int(f.recent_played)} trận**; có thể có đội bằng điểm.')
    else:notes+=['Chưa có trận đến mốc này; các đội giữ 0 trận.','Chưa đủ dữ liệu để nhận xét phong độ hoặc cú sút.']
    text='# Premier League 2025–2026\n\nDữ liệu trận đấu thật; báo cáo học tập.\n\n'+'\n\n'.join(f'{i}. {n}' for i,n in enumerate(notes,1))
    text+='\n\nNguồn: '+URL+'\n\nSHA256: `'+SHA256+'`\n\nSQL đã đối chiếu độc lập với pandas. Toàn file đã kiểm tra đủ 380 trận, 20 đội, 19 sân nhà + 19 sân khách mỗi đội.\n\nGiới hạn: bảng điểm tính từ kết quả (thắng 3, hòa 1), chưa có điều chỉnh hành chính/trừ điểm. Xếp hạng cùng điểm theo hiệu số rồi bàn thắng; đồng cả ba được cùng hạng (tên chỉ để hiển thị). Không tự xử lý đối đầu/play-off để quyết định quyền lợi chính thức. Mốc là hết ngày theo ngày nguồn, không phải bảng trực tiếp trong trận. Không có cầu thủ, xG, phút thi đấu hoặc vòng đấu chính thức; không suy vòng từ thứ tự ngày vì có đá bù. Cú sút thiếu giữ NULL, không đổi thành 0. Nguồn có thể sửa số liệu: bản này chốt snapshot, không tự cập nhật. Không suy nguyên nhân hoặc chất lượng tổng thể từ tương quan cú sút và bàn thắng.\n'
    (out/'report.md').write_text(text,encoding='utf-8')
    return out
def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default=str(DEFAULT_DB));p.add_argument('--as-of');p.add_argument('--out');a=p.parse_args()
    try:print(analyze(a.db,a.as_of,a.out))
    except (ValueError,OSError,AssertionError) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
