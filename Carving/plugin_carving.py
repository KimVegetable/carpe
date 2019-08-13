#-*- coding: utf-8 -*-
#!/usr/bin/python3

import os,sys,time,binascii
from multiprocessing import Process, Lock

from moduleInterface.defines   import *
from moduleInterface.interface import ModuleComponentInterface
from moduleInterface.actuator  import Actuator

sys.path.append(os.path.abspath(os.path.dirname(__file__)+"{0}include".format(os.sep)))
sys.path.append(os.path.abspath(os.path.dirname(__file__))+"{0}Code".format(os.sep))        # For carving module

from plugin_carving_defines import C_defy
from Include.carpe_db       import Mariadb


"""
    Key      :Value
    "name"   :"Carpe_Management",    # 모듈 이름
    "author" :"Gimin Hur",           # 모듈 작성자
    "ver"    :"0.1",                 # 모듈 버전
    "id"     :0,                     # onload 시 고유 ID (int 형)
    "param"  :"이미지 경로", "CASE명" # 모듈 파라미터
    "encode" :"utf-8",               # 인코딩 방식
    "base"   :0,                     # Base 주소(오프셋)
    "excl"   :False                  # 모듈의 유니크(배타적) 속성
"""


class Management(ModuleComponentInterface,C_defy):
    def __init__(self,debug=False,out=None,logBuffer=0x409600):
        super().__init__()
        self.__actuator  = Actuator()
        self.cursor      = None
        self.debug       = debug
        self.destPath    = ".{0}result".format(os.sep)
        self.hits        = {}
        self.lock        = Lock()
        self.__lp        = None
        self.logBuffer   = logBuffer
        self.out         = out
        self.defaultModuleLoaderFile = str(__file__).split(os.sep)[0]+os.sep+"config.txt"
        self.moduleLoaderFile        = self.defaultModuleLoaderFile

        if(type(self.out)==str):
            self.stdout  = str(__file__).split(os.sep)[0]+os.sep+str(self.out)
            self.out     = True
        else:
            self.out     = False
        
        self.__log_open()

    def __del__(self):
        try:
            if(self.__lp!=None):
                self.__lp.close()
        except:pass

    def __log_open(self):
        if(self.out==True):
            if(os.path.exists(self.stdout)):
                if(os.path.getsize(self.stdout)<self.logBuffer):
                    self.__lp = open(self.stdout,'a+')
                    return
            self.__lp = open(self.stdout,'w')
            self.__log_write("INFO","Main::Initiate carving plugin log.",always=True) 
        else:
            self.__lp   = None

    def __log_write(self,level,context,always=False,init=False):
        if((self.debug==True or always==True) and self.__lp==None):
            print("[{0}] At:{1} Text:{2}".format(level,time.ctime(),context))
        elif((self.debug==True or always==True) and (self.__lp!=None and init==True)):
            self.__lp.close()
            self.__log_open()
        elif((self.debug==True or always==True) and self.__lp!=None):
            try:
                self.__lp.write("[{0}]::At::{1}::Text::{2}\n".format(level,time.ctime(),context))
                self.__lp.flush()
            except:self.__lp==None

    def __get_file_handle(self,path):
        try:
            self.__fd = open(path,'rb')
        except:
            return ModuleConstant.Return.EINVAL_FILE
        self.__fd.seek(0,os.SEEK_SET)
        return ModuleConstant.Return.SUCCESS

    def __goto(self,offset,mode):
        return self.__fd.seek(offset,mode)

    def __cleanup(self):
        if(self.__fd!=None):
            try:self.__fd.close()
            except:pass
            self.__fd = None

    # @ Gibartes
    def __loadConfig(self):
        self.__log_write("INFO","Loader::Start to module load...",always=True)
        if(self.__actuator.loadModuleClassAs("module_config","ModuleConfiguration","config")==False):
            self.__log_write("ERR_","Loader::[module_config] module is not loaded. system exit.",always=True)
            return False
        self.__actuator.open("config",2,self.lock)
        self.__actuator.set( "config",ModuleConstant.FILE_ATTRIBUTE,ModuleConstant.CONFIG_FILE)
        self.__actuator.call("config",ModuleConstant.DESCRIPTION,"Carving Module List")

    # @ Gibartes
    def ___loadModule(self):
        self.__actuator.call("config",ModuleConstant.INIT,self.moduleLoaderFile)
        modlist = self.__actuator.call("config",ModuleConstant.GETALL,None).values()
        self.__log_write("INFO","Loader::[module_config] Read module list from {0}.".format(self.moduleLoaderFile),always=True)
        if(len(modlist)==0):
            self.__log_write("INFO","Loader::[module_config] No module to import.",always=True)
            return False
        for i in modlist:
            i   = i.split(",")
            if(len(i)!=3):continue
            res = self.__actuator.loadModuleClassAs(i[0],i[1],i[2])
            self.__log_write("INFO","Loader::loading module result [{0:>2}] name [{1:<16}]".format(res,i[0]),always=True)
            if(res==False):
                self.__log_write("WARN","Loader::[{0:<16}] module is not loaded.".format(i[0]),always=True)
        self.__log_write("INFO","Loader::Completed.",always=True)
        return True

    # @ Gibartes
    def __loadModule(self):
        self.__actuator.clear()
        self.__actuator.init()
        ret = self.__loadConfig()
        if(ret==False):
            return False
        return self.___loadModule()

    # @ Gibartes
    def __call_sub_module(self,_request,start,end,cluster,etype='euc-kr'):
        self.__actuator.set(_request, ModuleConstant.FILE_ATTRIBUTE,self.I_path)  # File to carve
        self.__actuator.set(_request, ModuleConstant.IMAGE_BASE, start)  # Set offset of the file base
        self.__actuator.set(_request, ModuleConstant.IMAGE_LAST, end)
        self.__actuator.set(_request, ModuleConstant.CLUSTER_SIZE, cluster)
        self.__actuator.set(_request, ModuleConstant.ENCODE, etype)
        return self.__actuator.call(_request, None, None)

    # @ Jimin_Hur
    def __carving_conn(self,cred):
        if(cred.get('init')==True):
            conn = pymysql.connect(host=cred.get('ip'),port=cred.get('port'),user=cred.get('id'),passwd=cred.get('password'))
            conn.cursor().execute("create database {0}".format(cred.get('category')))
            conn.close()
            del conn
        try :
            db = Mariadb()
            cursor = db.i_open(cred.get('ip'),cred.get('port'),cred.get('id'),cred.get('password'),cred.get('category'))
            return cursor
        except Exception :
            self.__log_write("ERR_","Database::Carving DB(local) connection ERROR.")
            exit(C_defy.Return.EFAIL_DB)

    # @ Jimin_Hur
    def __db_conn_create(self,cred):
        db = Mariadb()
        # CARPE DB 연결 및 정보 추출
        try :
            cursor1 = db.i_open(cred.get('ip'),cred.get('port'),cred.get('id'),cred.get('password'),cred.get('category'))
            cursor1.execute('select * from carpe_block_info where p_id = %s', self.case)
            data = cursor1.fetchall()
            cursor1.execute('show create table carpe_block_info')
            c_table_query = cursor1.fetchone()
        except Exception :
            self.__log_write("ERR_","Database::CARPE DB(master) connection ERROR.")
            exit(C_defy.Return.EFAIL_DB)
        # Table 존재여부 확인 및 테이블 생성
        try :
            self.cursor.execute('show tables like "carpe_block_info"')
            temp = self.cursor.fetchone()
            if temp is not None :
                pass
            else :
                self.cursor.execute(c_table_query[1])
                
            self.cursor.execute('select count(*) from carpe_block_info where p_id = %s', self.case)
            init_count = self.cursor.fetchone()
            if len(data) == init_count[0] :
                self.__log_write("WARN","Database::This case is already finished Convert DB processing in carving.")
                pass
            else :
                start = time.time()
                self.cursor.execute('start transaction')
                for row in data :
                    self.cursor.execute('insert into carpe_block_info values (%s,%s,%s,%s)',(row[0],row[1],row[2],row[3]))
                self.cursor.execute('commit')
                self.__log_write("DBG_","copy db time : {0}".format(time.time() - start))
                self.cursor.execute(db.CREATE_HELPER['datamap'])
                self.__convert_db()
        except Exception:
            self.__log_write("ERR_","Database::Unallocated area DB porting ERROR")
        cursor1.close()
        db.close()

    # @ Jimin_Hur
    def __convert_db(self):
        try :
            self.cursor.execute('select * from carpe_block_info where p_id = %s',self.case)
            data = self.cursor.fetchall()
            start = time.time()
            # 모든 미할당 블록을 DB 레코드로 변경하는 코드부분 [NULL 영역.]
            for row in data :
                map_id = ((row[2] * self.blocksize)+self.par_startoffset) / self.blocksize
                end_id = ((row[3] * self.blocksize)+self.par_startoffset) / self.blocksize
                self.cursor.execute('start transaction')
                while map_id <= end_id :
                    sql = 'insert into datamap (blk_num,block_id) values(%s, %s)'
                    self.cursor.execute(sql,(map_id, row[0]))
                    map_id = map_id + 1
                self.cursor.execute('commit')
            self.__log_write("DBG_","converting time : {0}.".format(time.time() - start))
        except Exception :
            self.__log_write("ERR_","Database::Check signature module ERROR.")

    # @ Jimin_Hur
    def __signature_scan(self):
        try :
            FP = open(self.I_path,'rb')
            FP.seek(self.par_startoffset)
            C_offset = self.par_startoffset
            Max_offset = os.path.getsize(self.I_path)
            flag = 0
            isthere = 0

            # (현) Block 단위로 Signature 스캔 진행
            # Block 안의 Sector 단위에 대한 처리 방법 고려하기 - Schema
            start = time.time()
            while C_offset <= Max_offset :
                buffer = FP.read(self.blocksize)
                for key in C_defy.Signature.Sig :
                    temp = C_defy.Signature.Sig[key]
                    if binascii.b2a_hex(buffer[temp[1]:temp[2]]) == temp[0] :
                        # 특정 파일포맷에 대한 추가 검증 알고리즘
                        if key == 'aac_1' or key == 'aac_2' :
                            if binascii.b2a_hex(buffer[7:8]) == b'21' :
                                flag = 1
                        # DB 업데이트
                        isthere = self.cursor.execute('select * from datamap where blk_num = %s', C_offset/self.blocksize)
                        if flag == 0 and isthere == 1:
                            self.cursor.execute('update datamap set blk_type = %s,blk_sig = %s, blk_stat = %s where blk_num = %s',('sig',key,'carving',C_offset/self.blocksize))
                        #print("[DEBUG] : Find : ",key,"  Offset : ",hex(C_offset))
                    flag = 0
                    isthere = 0
                C_offset += self.blocksize
                FP.seek(C_offset)
            self.__log_write("DBG_","Carving::converting time : {0}.".format(time.time() - start))
        except Exception :
            self.__log_write("ERR_","Carving::Fast Signature Detector ERROR.")

    # @ Jimin_Hur
    def __carving(self):
        self.cursor.execute('select block_id, blk_num, blk_sig from datamap where blk_sig is not null')
        data = self.cursor.fetchall()
        i        = 0
        total    = len(data)
        disable  = False
        self.hit = {}

        if not os.path.exists(self.destPath):
            os.mkdir(self.destPath)

        errno = self.__get_file_handle(self.I_path)
        if(errno==ModuleConstant.Return.EINVAL_FILE):
            self.__log_write("ERR_","Carving::Cannot create a file handle.")
            disable = True

        for sigblk in data :
            
            if (self.hit.get(data[i][2])==None):
                self.hit.update({data[i][2]:[0,0]})
            
            value   = self.hit.get(data[i][2])
            self.hit.update({data[i][2]:[value[0]+1,value[1]]})
            value   = self.hit.get(data[i][2])
            
            current = data[i][1]*self.blocksize

            # 맨 마지막 레코드
            if i+1 == total:
                end_pos = os.path.getsize(self.I_path)
                result  = self.__call_sub_module(data[i][2],current,end_pos,self.blocksize)

                if(type(result)==tuple):
                    result = [list(result)]

                if(len(result[0])==4):
                    result[0].pop(0)

                #print(data[i][2],hex(data[i][1]*self.blocksize),result)
                if(result[0][1]>0):
                    res = self.__extractor(data[i][2],result,disable) #파일 추출 모듈
                    if(res!=ModuleConstant.Return.EINVAL_NONE):
                        self.hit.update({data[i][2]:[value[0],value[1]+1]})

            else :
                # 같은 블록에 여러개의 sig가 발견
                if sigblk[0] == data[i+1][0] :
                    result = self.__call_sub_module(data[i][2],current,data[i+1][1]*self.blocksize,self.blocksize)
                    
                    if(type(result)==tuple):
                        result = [list(result)]

                    if(len(result[0])==4):
                        result[0].pop(0)

                    #print(data[i][2],hex(data[i][1]*self.blocksize),result)
                    if(result[0][1]>0):
                        res = self.__extractor(data[i][2],result,disable) #파일 추출 모듈
                        if(res!=ModuleConstant.Return.EINVAL_NONE):
                            self.hit.update({data[i][2]:[value[0],value[1]+1]})
                
                # 다른 블록으로 변경됨

                else :
                    self.cursor.execute('select blk_num from datamap where blk_num > %s and block_id = %s order by blk_num desc',(sigblk[1],sigblk[0]))
                    end_pos = self.cursor.fetchone()
                    
                    if(end_pos!=None):
                        result = self.__call_sub_module(data[i][2],current,end_pos[0]*self.blocksize,self.blocksize)
                        if(type(result)==tuple):
                            result = [list(result)]

                        if(len(result[0])==4):
                            result[0].pop(0)
                        
                        #print(data[i][2],hex(data[i][1]*self.blocksize),result)
                        if(result[0][1]>0):
                            res = self.__extractor(data[i][2],result,disable) #파일 추출 모듈
                            if(res!=ModuleConstant.Return.EINVAL_NONE):
                                self.hit.update({data[i][2]:[value[0],value[1]+1]})

                    else:
                        # --------------------------------------------
                        # 데이터가 있음에도 불구하고 리턴 값 None 추가 처리 요함 (DB 파트 협의 필요)
                        # 임시 처리 : (블록 크기만큼)
                        result = self.__call_sub_module(data[i][2],current,current+self.blocksize,self.blocksize)
                        if(type(result)==tuple):
                            result = [list(result)]

                        if(len(result[0])==4):
                            result[0].pop(0)
                        
                        #print(data[i][2],hex(data[i][1]*self.blocksize),result)
                        if(result[0][1]>0):
                            res = self.__extractor(data[i][2],result,disable) #파일 추출 모듈
                            if(res!=ModuleConstant.Return.EINVAL_NONE):
                                self.hit.update({data[i][2]:[value[0],value[1]+1]})
                        # --------------------------------------------

            i += 1

    # @ Jimin_Hur
    # Extract file(s) from image.
    def __extractor(self,extension,result,disable):
        if(disable==True):
            return ModuleConstant.Return.EINVAL_TYPE

        path = self.destPath+os.sep+extension+os.sep
        if(not os.path.exists(path)):
            self.__log_write("INFO","Extract::create a result directory at {0}".format(path))
            os.mkdir(path)

        fname  = path+str(hex(result[0][0]))+"."+extension
        length = len(result)
        fd     = None

        try:
            fd = open(fname,'wb')
        except:
            self.__log_write("ERR_","Extract::an error while creating file.".format(path))
            return ModuleConstant.Return.EINVAL_NONE

        if(length==1):
            wrtn = 0
            byte2copy = result[0][1]
            self.__goto(result[0][0],os.SEEK_SET)

            while(byte2copy>0):
                if(byte2copy<self.sectorsize):
                    data = self.__fd.read(byte2copy)
                    wrtn +=fd.write(data)
                    byte2copy-=byte2copy
                    break
                data = self.__fd.read(self.sectorsize)
                wrtn +=fd.write(data)
                byte2copy-=self.sectorsize
            fd.close()
        else:
            wrtn = 0
            i    = 0
            while(i<length):
                byte2copy = result[i][1]
                self.__goto(result[i][0],os.SEEK_SET)

                while(byte2copy>0):
                    if(byte2copy<self.sectorsize):
                        data     = self.__fd.read(byte2copy)
                        zerofill = bytearray(self.sectorsize-byte2copy)
                        wrtn +=fd.write(data)
                        wrtn +=fd.write(zerofill)
                        byte2copy-=byte2copy
                    else:
                        data = self.__fd.read(self.sectorsize)
                        wrtn +=fd.write(data)
                        byte2copy-=self.sectorsize
                i+=1
            fd.close()
        
        self.__log_write("DBG_","Extract::type:{0} name:{1} copied:{2} bytes details:{3}".format(extension,fname,wrtn,result))

        return (fname,wrtn)


    # @ Module Interface

    def module_open(self,id=1):             # Reserved method for multiprocessing
        pass
    def module_close(self):                 # Reserved method for multiprocessing
        pass
    def set_attrib(self,key,value):         # 모듈 호출자가 모듈 속성 변경/추가하는 method interface
        pass
    def get_attrib(self,key,value=None):    # 모듈 호출자가 모듈 속성 획득하는 method interface
        pass

    def execute(self,cmd=None,option=None):
        if(cmd==ModuleConstant.PARAMETER):
            self.data            = 0
            self.case            = option.get("case",None)
            self.blocksize       = option.get("block",4096)
            self.sectorsize      = option.get("sector",512)
            self.par_startoffset = option.get("start",0)
            self.I_path          = option.get("path",None)
            self.destPath        = option.get("dest",".{0}result".format(os.sep))
            self.config          = option.get("config",self.defaultModuleLoaderFile)
            self.__log_write("INFO","Main::Request to set parameters.",always=True)

        elif(cmd==ModuleConstant.LOAD_MODULE):
            self.__log_write("INFO","Main::Request to load module(s).",always=True)
            return self.__loadModule()

        elif(cmd==ModuleConstant.CONNECT_DB):
            self.__log_write("INFO","Main::Request to connect to local database.",always=True)  
            self.cursor = self.__carving_conn(option)

        elif(cmd==ModuleConstant.CREATE_DB):
            if(self.cursor!=None):
                self.__log_write("INFO","Main::Request to connect to remote database and update local database.",always=True) 
                self.__db_conn_create(option)

        elif(cmd==ModuleConstant.DISCONNECT_DB):
            self.__log_write("INFO","Main::Request to clean up.",always=True) 
            if(self.cursor!=None):
                self.cursor.close()
                self.cursor = None
            else:
                self.__log_write("WARN","Main::Database handle is already closed.",always=True) 

        elif(cmd==ModuleConstant.EXEC and option==None):
            self.__log_write("","",always=True,init=True)
            self.__log_write("INFO","Main::Request to run carving process.",always=True)  
            self.__signature_scan() # 시그니처 탐지
            start = time.time()
            self.__carving()        # 카빙 동작
            self.__log_write("DBG_","Carving::carving time : {0}.".format(time.time() - start))
            self.__log_write("INFO","Carving::result:{0}".format(self.hit),always=True)


if __name__ == '__main__':
    manage = Management(debug=False,out="carving.log")

    res = manage.execute(ModuleConstant.LOAD_MODULE)

    if(res==False):
        sys.exit(0)

    manage.execute(ModuleConstant.PARAMETER,
                    {
                        "case":"TEST_2",
                        "block":4096,
                        "sector":512,
                        "start":0x10000,
                        "path":"D:\\iitp_carv\\[NTFS]_Carving_Test_Image1.001"
                    }
    )
    
    manage.execute(ModuleConstant.CONNECT_DB,
                    {
                        "ip":'localhost',
                        "port":0,
                        "id":'root',
                        "password":'dfrc4738',
                        "category":'carving',
                        "init":False
                    }
    )
     
    manage.execute(ModuleConstant.CREATE_DB,
                    {
                        "ip":'218.145.27.66',
                        "port":23306,
                        "id":'root',
                        "password":'dfrc4738',
                        "category":'carpe_3'
                    }
    )
    
    manage.execute(ModuleConstant.EXEC)

    manage.execute(ModuleConstant.DISCONNECT_DB)

    sys.exit(0)