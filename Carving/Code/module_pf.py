#-*- coding: utf-8 -*-

#!/usr/bin/python3

"""
The default attribute of module :
    "name"   :"default",            # Module 이름
    "author" :"carpe",              # Module 제작자
    "ver"    :"0.0",                # Module 버젼
    "param"  :None,                 # Module 파라미터
    "encode" :"utf-8",              # Module 인코딩
    "base"   :0                     # File image base to carve

"""
import os,sys

from moduleInterface.defines   import *
from moduleInterface.interface import ModuleComponentInterface
#from defines         import *
#from interface       import ModuleComponentInterface
from structureReader import structureReader as sr
#from structureReader import StructureReader    as parser
#from structureReader import _PrefetchStructure as structure

class ModulePrefetch(ModuleComponentInterface):
    MAM_SIG  = b'MAM\x04'
    SCCA_SIG = b'SCCA'

    def __init__(self):
        super().__init__()                  # Initialize Module Interface
        self.fileSize   = 0
        self.offset     = list()
        self.missing    = 0
        self.parser     = sr.StructureReader()

        self.set_attrib(ModuleConstant.NAME,"pf")
        self.set_attrib(ModuleConstant.VERSION,"0.1")
        self.set_attrib(ModuleConstant.AUTHOR,"HK")
    
    def __reinit__(self):
        self.fileSize   = 0
        self.offset     = list()
        self.missing    = 0

    def __del__(self):
        self.parser.cleanup()

    """ Module Methods """

    def __evaluate(self):
        fn = self.attrib.get(ModuleConstant.FILE_ATTRIBUTE)
        if(fn==None):
            return ModuleConstant.Return.EINVAL_ATTRIBUTE
        try:
            fd = os.open(fn,os.O_RDONLY)
            os.close(fd)
        except:return ModuleConstant.Return.EINVAL_FILE
        return ModuleConstant.Return.SUCCESS

    # ShellItemList와 FileLocationInfo의 이름 필드 비교
    def __read(self,offset):
        header = sr._PrefetchStructure()
        size   = 0

        result = self.parser.execute(header.MAMHeader,'byte',offset,os.SEEK_SET,'little')
        if(result==False):
            return (False,0,-1,ModuleConstant.INVALID)

        # SCCA
        if(self.parser.get_value('signature')!=ModulePrefetch.MAM_SIG):
            self.parser.execute(header.SCCAHeader,'byte',offset,os.SEEK_SET,'little')
            if(self.parser.get_value('signature')!=ModulePrefetch.SCCA_SIG):
                return (False,0,-1,ModuleConstant.INVALID)
            expected = int.from_bytes(self.parser.get_value('size'),'little')
            if(expected<self.parser.get_size()):
                return (False,0,-1,ModuleConstant.INVALID)

            self.parser.execute(header.FileInfoCommon,'int',0,os.SEEK_CUR,'little')
            volumeInfo = self.parser.get_value('vio')+self.parser.get_value('vis')
            fnameInfo  = self.parser.get_value('fnso')+self.parser.get_value('fnss')

            if(expected==max(volumeInfo,fnameInfo)):
                 return (True,offset,expected,ModuleConstant.FILE_ONESHOT)

            return (False,0,-1,ModuleConstant.INVALID)

        # MAM (Lzxpress)
        else:
            expected = int.from_bytes(self.parser.get_value('size','little'))
            if(expected<self.parser.get_size()):
                return (False,0,-1,ModuleConstant.INVALID)

            return (True,offset,expected,ModuleConstant.FILE_ONESHOT)
        
    def carve(self):
        self.__reinit__() 
        self.parser.get_file_handle(
            self.get_attrib(ModuleConstant.FILE_ATTRIBUTE),
            self.get_attrib(ModuleConstant.IMAGE_BASE)
        )

        offset  = self.get_attrib(ModuleConstant.IMAGE_BASE)     
        self.parser.goto(offset,os.SEEK_SET)

        res = self.__read(offset)
        if(res[0]==True):
            self.offset.append((res[1],res[2]))
            self.fileSize += res[2]
            offset+=res[2]
        else:
            self.missing+=1
        self.parser.cleanup()

    """ Interfaces """

    def module_open(self,id):               # Reserved method for multiprocessing
        super().module_open()

    def module_close(self):                 # Reserved method for multiprocessing
        pass

    def set_attrib(self,key,value):         # 모듈 호출자가 모듈 속성 변경/추가하는 method interface
        self.update_attrib(key,value)

    def get_attrib(self,key,value=None):    # 모듈 호출자가 모듈 속성 획득하는 method interface
        return self.attrib.get(key)

    def execute(self,cmd=None,option=None): # 모듈 호출자가 모듈을 실행하는 method
        ret = self.__evaluate()
        if(ret!=ModuleConstant.Return.SUCCESS):
            return [(False,ret,ModuleConstant.INVALID)]
        self.carve()
        if(self.offset==[]):
            return [(False,0,ModuleConstant.INVALID)]
        return self.offset                  # return <= 0 means error while collecting information


if __name__ == '__main__':

    pf = ModulePrefetch()
    try:
        pf.set_attrib(ModuleConstant.FILE_ATTRIBUTE,sys.argv[1])   # Insert .pf File
    except:
        print("This moudule needs exactly one parameter.")
        sys.exit(1)

    pf.set_attrib(ModuleConstant.IMAGE_BASE,0)                     # Set offset of the file base
    pf.set_attrib(ModuleConstant.CLUSTER_SIZE,1024)
    cret = pf.execute()
    print(cret)

    sys.exit(0)
