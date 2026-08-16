try:
    import pymysql
except ImportError:
    pymysql = None

if pymysql:
    pymysql.install_as_MySQLdb()
