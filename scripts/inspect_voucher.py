import sqlite3
c = sqlite3.connect('F:/sscegov.com/django/db.sqlite3')
print(c.execute('pragma table_info(web_voucherconfiguration)').fetchall())
print(c.execute('pragma index_list(web_voucherconfiguration)').fetchall())
print(c.execute('select user_id, category, series, count(*) from web_voucherconfiguration group by user_id, category, series having count(*) > 1').fetchall())
