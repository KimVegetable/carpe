import pymysql
from filesystem_analyzer import carpe_file

class Mariadb(object):
	#To Do
	# Tune the columns
	TABLE_INFO = {
		"case_info":{"case_id":"VARCHAR PRIMARY KEY", "case_name":"TEXT", "administrator":"TEXT", "create_date":"DATETIME", "description":"TEXT"},
		"investigator":{"id":"TEXT PRIMARY KEY", "name":"TEXT", "password":"TEXT", "acl":"TEXT"},
		"evidence_info":{"evd_id":"VARCHAR PRIMARY KEY", "evd_name":"TEXT", "evd_path":"TEXT", "tmp_path":"TEXT", "case_id":"VARCHAR", "main_type":"TEXT", "sub_type":"TEXT", "timezone":"TEXT", "acquired_date":"DATETIME", "md5":"TEXT", "sha1":"TEXT", "sha3":"TEXT", "process_state":"INTEGER"},
		"partition_info":{"par_id":"VARCHAR PRIMARY KEY", "par_name":"TEXT", "par_id":"VARCHAR", "par_type":"TEXT", "sector_size":"INTEGER", "par_size":"BIGINT", "md5":"TEXT", "sha1":"TEXT", "sha3":"TEXT", "start_sector":"BIGINT"},
		"fs_info":{"fs_id":"VARCHAR", "par_id":"VARCHAR PRIMARY KEY", "block_size":"INTEGER", "block_count":"BIGINT", "root_inum":"INTEGER", "first_inum":"INTEGER", "last_inum":"INTEGER"},
		"file_info":{"id":"BIGINT PRIMARY KEY", "file_id":"BIGINT", "par_id":"VARCHAR", "inode":"TEXT", "name":"TEXT", "meta_seq":"BIGINT", "type":"INTEGER", "dir_type":"INTEGER", "meta_type":"INTEGER", "meta_flags":"INTEGER", "size":"BIGINT",
					"mtime":"BIGINT", "atime":"BIGINT", "ctime":"BIGINT", "etime":"BIGINT", "mtime_nano":"BIGINT", "atime_nano":"BIGINT", "ctime_nano":"BIGINT", "etime_nano":"BIGINT",
					"additional_mtime":"BIGINT", "additional_atime":"BIGINT", "additional_ctime":"BIGINT", "additional_etime":"BIGINT", "additional_mtime_nano":"BIGINT", "additional_atime_nano":"BIGINT", "additional_ctime_nano":"BIGINT", "additional_etime_nano":"BIGINT",
					"mode":"INTEGER", "uid":"INTEGER", "gid":"INTEGER",
                                        "md5":"TEXT", "sha1":"TEXT", "sha3":"TEXT",
                                        "parent_path":"TEXT", "extension":"TEXT",
                                        "parent_id":"BIGINT", "bookmark":"BOOLEAN", "ads":"INTEGER"},
		"block_info":{"par_id":"VARCHAR", "start":"BIGINT", "end":"BIGINT"}
	}
	#To Do
	#Fill all the values
	INSERT_HELPER = {
		"case_info":"%s, %s, %s, %s, %s",
		"investigator":"%s, %s, %s, %s",
		"evidence_info":"%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %d",
		"partition_info":"%s, %s, %s, %s, %d, %s, %s, %s, %s, %s",
		"fs_info":"%s, %s, %d, %s, %d, %d, %d",
		"file_info":"%s, %s, %s, %s, %s, %s, %d, %d, %d, %d, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %d, %d, %d, %s, %s, %s, %s, %s, %s, %d, %d",
		"block_info":"%s, %s, %s"
	}

	CREATE_HELPER = {
		"case_info":"CREATE TABLE case_info (case_id VARCHAR(100) NOT NULL, case_name TEXT NOT NULL, administrator TEXT NOT NULL, create_date DATETIME NOT NULL, description TEXT, PRIMARY KEY(case_id));",
		"investigator":"CREATE TABLE investigator (id varchar(255) NOT NULL, name varchar(100) NOT NULL, password varchar(100) NOT NULL, acl TEXT NULL, PRIMARY KEY(id));",
		"evidence_info":"CREATE TABLE evidence_info (evd_id VARCHAR(100) NOT NULL, evd_name TEXT NOT NULL, evd_path TEXT NOT NULL, tmp_path TEXT NOT NULL, case_id VARCHAR(100) NOT NULL, main_type TEXT NOT NULL, sub_type TEXT NOT NULL, timezone TEXT NOT NULL, acquired_date DATETIME, md5 TEXT, sha1 TEXT, sha3 TEXT, process_state INT(11) DEFAULT 0, PRIMARY KEY(evd_id), FOREIGN KEY(case_id) REFERENCES case_info(case_id));",
		"partition_info":"CREATE TABLE partition_info (par_id VARCHAR(100) NOT NULL, par_name TEXT NOT NULL, evd_id VARCHAR(100) NOT NULL, par_type TEXT NOT NULL, sector_size INT(11) NOT NULL DEFAULT 0, par_size BIGINT NOT NULL DEFAULT 0, md5 TEXT, sha1 TEXT, sha3 TEXT, start_sector BIGINT NOT NULL, PRIMARY KEY(par_id), FOREIGN KEY(evd_id) REFERENCES evidence_info(evd_id));",
		"fs_info":"CREATE TABLE fs_info (fs_id VARCHAR(100) NOT NULL, par_id VARCHAR(100) NOT NULL, block_size INT(11), block_count BIGINT, root_inum INT(11), first_inum INT(11), last_inum BIGINT, PRIMARY KEY(fs_id), FOREIGN KEY(par_id) REFERENCES partition_info(par_id));",
		"file_info":"CREATE TABLE file_info (id BIGINT NOT NULL AUTO_INCREMENT, file_id BIGINT NOT NULL, par_id VARCHAR(100) NOT NULL, inode TEXT, name TEXT NOT NULL, meta_seq BIGINT, type INTEGER, dir_type INTEGER, meta_type INTEGER, meta_flags INTEGER, size BIGINT, mtime BIGINT, atime BIGINT, ctime BIGINT, etime BIGINT, mtime_nano BIGINT, atime_nano BIGINT, ctime_nano BIGINT, etime_nano BIGINT, additional_mtime BIGINT, additional_atime BIGINT, additional_ctime BIGINT, additional_etime BIGINT, additional_mtime_nano BIGINT, additional_atime_nano BIGINT, additional_ctime_nano BIGINT, additional_etime_nano BIGINT, mode INTEGER, uid INTEGER, gid INTEGER, md5 TEXT, sha1 TEXT, sha3 TEXT, parent_path TEXT, extension TEXT, parent_id BIGINT, bookmark BOOLEAN, PRIMARY KEY(id), FOREIGN KEY(par_id) REFERENCES partition_info(par_id));",
		"block_info":"CREATE TABLE block_info (par_id VARCHAR(100) NOT NULL, start BIGINT, end BIGINT);"
	}

	# To Do 
	# query for select specific file's metadata such as inode by extension 
	PREPARED_QUERY = {		
	}

	def __init__(self):
		self._conn = None

	def open(self):
		try:
			self._conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', passwd='dfrc4738', db='carpe',charset='utf8',autocommit=True)
		except Exception:
			self._conn=None
			print("db connection error")

	def commit(self):
		try:
			self._conn.commit()
		except Exception:
			print("db commit error")

	def close(self):
		try:
			self._conn.close()
		except Exception:
			print("db connection close error")

	def check_table_exist(self, table_name):
		if (self._conn is not None):
			query = "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME ="+ table_name
			ret = self.execute_query(query)
			self.close()
			if ret[0] == 1:				
				return True
			else:
				return False
		else:
			self.open()
			return self.check_table_exist(table_name)

	def initialize(self):
		self.open()
		for table_name in self.TABLE_INFO.keys():
			if not (self.check_table_exist(table_name)):
				self.execute_query(self.CREATE_HELPER[table_name])
		self.commit()
		self.close()		

	def files_object(self, files):
		print(files)

	def bulk_execute(self, query, values):
		try:
			cursor = self._conn.cursor()
		except Exception:
			print("db cursor error")
			return -1
		try:
			cursor.executemany(query, values)
			#cursor.executemany
			data = cursor.fetchone()
			cursor.close()
			return data			
		except Exception:
			print("db execution error")
			return -1

	def insert_query_builder(self, table_name):
		if table_name in self.TABLE_INFO.keys():
			query = "INSERT INTO {0} (".format(table_name)
			query += "".join([lambda:column +") ", lambda:column+", "][column!=sorted(self.TABLE_INFO[table_name].keys())[-1]]() for column in (sorted(self.TABLE_INFO[table_name].keys())))
			#query += "VALUES ({})".format(self.INSERT_HELPER[table_name])
		return query

	def execute_query(self, query):
		cursor = self._conn.cursor()
		try:
			cursor.execute(query)
			#cursor.executemany
			data = cursor.fetchone()
			cursor.close()
			return data
		except Exception:
			print(query)
			print("db execution error")
			return -1

	def execute_query_mul(self ,query):
		cursor = self._conn.cursor()
		try:
			cursor.execute(query)
			#cursor.executemany
			data = cursor.fetchall()
			cursor.close()
			return data
		except Exception:
			print("db execution error")
			return -1
