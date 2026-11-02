# Lời giải gợi ý

Chạy trong notebook bằng `read_sql(sql, params)`; không gõ SQL vào PowerShell.

1–2: `SELECT * FROM matches ORDER BY played_on, kickoff_time LIMIT 10`; đổi DESC cho cả hai.
3: `SELECT * FROM teams WHERE name LIKE '%Man%'`.
4: `WHERE played_on BETWEEN '2025-12-01' AND '2025-12-31'`.
5: xem sql/analysis.sql, hai alias h và a.
6: matches380; team_matches760 nếu hết mùa. Không gọi760là số trận.
7–9: xem `team_cte()` trong epl_lab/analysis.py, CASE theo result rồi GROUP BY team_id.
10: `queries(db,'2025-08-01')['standings']`:20đội,0trận, chung hạng1.
11: GROUP BY team_id,venue.
12: cùng truy vấn11, `HAVING SUM(points)>=20` khi venue='away'.
13: ROW_NUMBER partition team_id order ngày/giờ/id DESC rồi rn<=5; hiển thị recent_played.
14: `LAG(points) OVER(PARTITION BY team_id ORDER BY played_on,kickoff_time,match_id)`; lọc ngày trình bày sau khi tính LAG.
15: COUNT(*) - COUNT(home_shots); không thay thiếu bằng0.
16: substr(played_on,1,7), SUM(home_goals+away_goals).
17: tổng GF=GA, mỗi bàn của đội này là bàn thua của đội kia.
18: xem buổi7: SQLite memory, BEGIN/INSERT/ROLLBACK, đếm0.
19: `reconcile(db,'2026-01-01')`; pandas phải đọc bảng nguồn rồi tự mở rộng hai phía.
20: số trận/phạm vi; đội và điểm; phong độ kèm số trận. Không suy chất lượng tổng thể hoặc nguyên nhân từ tương quan.
