import os
import socket
import base64
import logging
import traceback
import time
import shutil
import uuid
import urllib.parse
import numpy as np
import uvicorn as uvicorn
from typing import Tuple,List
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from fastapi.responses import FileResponse, JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import  CORSMiddleware
from fastapi import FastAPI, HTTPException, Header, Depends, UploadFile,File,Body

load_dotenv(os.getcwd()+r"\.env")

MONGODB_HOST = os.getenv("DB_HOST", "localhost")
MONGODB_PORT = os.getenv("DB_PORT", "27017")
MONGODB_USER = os.getenv("DB_USER", "default_user")
MONGODB_PASSWORD = os.getenv("DB_PASSWORD", "default_password")
CSRF_TOKEN = os.getenv("CSRF_TOKEN")
COOKIE_KEY = os.getenv("COOKIE_KEY")
COOKIE_VALUE = os.getenv("COOKIE_VALUE")
DEBUG_MODE=os.getenv("DEBUG","FALSE").upper()
if DEBUG_MODE == "TRUE":
    db_pj_list = "project_list_debug"
    request_form = "request_form_debug"
    record = "using_record_debug"
else:
    db_pj_list = "project_list"
    request_form = "request_form"
    record = "using_record"
encoded_cookie_key = base64.b64encode(COOKIE_KEY.encode()).decode()
encoded_cookie_value = base64.b64encode(COOKIE_VALUE.encode()).decode()
db_url=f"{MONGODB_HOST}:{MONGODB_PORT}"


# ? docs_url=None, redoc_url=None (正式版本可以將文件功能隱藏)
app=FastAPI()

# create folder for files
UPLOAD_FOLDER = "FilesUpload"
if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

program = 'rf-simulation-request'
logPath = os.getcwd()+r"\log"

if not os.path.isdir(logPath):
    os.mkdir(logPath)
logFormatter = "%(asctime)s [%(levelname)s] <%(funcName)s> : %(message)s"
dateFormat = "%Y-%m-%d %H:%M:%S"
today = datetime.today()

logging.basicConfig(filename=os.path.join(logPath, today.strftime("%Y-%m-%d") +"_"+ program +".log"),
                    format=logFormatter, datefmt=dateFormat, level=logging.DEBUG)

logging.info(program)
logging.info("[Start]")

def is_production():
    hostname = socket.gethostname()
    prod_hosts = {"tpea40011719","tpea90087784","tper54009852"}
    return hostname.lower() in {h.lower() for h in prod_hosts}

is_product_env=is_production()

# TODO: CORS設定
if is_product_env:
    # origins = ["https://erfdm.wistron.com"]
    # secure_set =True
    origins = ["*"]
    secure_set =False
else:
    origins = ["*"]
    secure_set =False

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["X-CSRF-Token"],
)

# TODO: 修改文件版本與名稱
# ? redoc 上面顯示的名稱和版本，有更新需要修改
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="RF Simulation Request",
        version="1.0.0",
        description="RF Simulation Request.",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema
# --------------------------- 資安設定 ---------------------------- #
# UkZfU2ltdWxhdGlvbl8yMDI1MDUyNw==
def verify_csrf_token(x_csrf_token: str = Header(None, alias="X-CSRF-Token")):
    decoded_string = base64.b64decode(x_csrf_token).decode("utf-8")
    if decoded_string != CSRF_TOKEN:
        logging.error(f"{x_csrf_token=}")
        logging.error(f"{decoded_string=}")
        raise HTTPException(status_code=403, detail="Invalid CSRF Token")
    return True
# 可以考慮檢查 cookie key 和 value
# class CookieMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request, call_next):
#         response = await call_next(request)
#         # 在每個回應中設置 Cookie
#         response.set_cookie(
#             key = encoded_cookie_key,
#             value = encoded_cookie_value,
#             httponly = True,  
#             samesite = "Strict", 
#             secure = secure_set
#         )
#         return response

# # 添加中間件
# app.add_middleware(CookieMiddleware)


# --------------------------------- API for overall status ------------------------------------- #
@app.get("/data/update_overall_status/{project_id}")
def update_overall_status(project_id:str):
    """ 
    由PowerBI link 進入 project 時，會依照 project ID 抓取 project_list 的 project info, 若同時有 request_form 也會抓取必且以create_time 由新排到舊。
    最後整理成 dict_respond 轉json 送給前端。
    會判斷四個燈號 ['Light_of_pj_info','Light_of_request_form','Light_of_accept_request','Light_of_simulation_finished'] 並且以四個燈號判斷 overall light 和 Current stage。
    dd 為 RFQ -21 Days Due Day(PO設定的)
    Args:
        project_id (str): ProjectId, 單一案子一個，不應該重複

    Raises:
        Error Message:{"Error": f"Missing Project: {project_id}"},400
        Error Message:{"Error": f"Duplicated ProjectID: {project_id}"},400
        Error Message:{"Error": "No RFQ Date"},400
        Error Message:{"Error": "No RFI Date"},400
        Error Message:{"Error": f"Missing key : {missing_fields}"},400
        Error Message:{"Error": f"{project_id=} Updated Overall Status Failed."}},400
        Error Message: {"Error": str(NameError)},400
        HTTPException: Any unexpected error.500, INTERNAL_ERROR to Web

    Returns:
        dict:{
            "project":dict_project,
            "request_form":list_request_form,
            "records":list_record
            }
    """    
    conn1 = None
    conn2 = None
    conn3 = None
    try:
        logging.info(f"Get ProjectID: {project_id}")
        conn1,project_list_col=connect_mongodb("RFSimulationRequest",db_pj_list)
        conn2,request_form_col=connect_mongodb("RFSimulationRequest",request_form)
        conn3,records_col=connect_mongodb("RFSimulationRequest",record)
        list_project = list(project_list_col.find({"ProjectId": project_id},{"_id": 0}))
        list_request_form = list(request_form_col.find({"ProjectId": project_id},{"_id": 0}).sort("create_time",-1))
        list_record= list(records_col.find({"ProjectId": project_id},{"_id": 0}).sort("time",-1))
        if not len(list_project) :
            logging.info(f"Missing Project: {project_id}")
            return JSONResponse(content={"Error": f"Missing Project: {project_id}"}, status_code=400)
        if len(list_project) > 1:
            logging.info(f"Duplicated ProjectID: {project_id}")
            return JSONResponse(content={"Error": f"Duplicated ProjectID: {project_id}"}, status_code=400)
        dict_project = list_project[0]
        check_key = ["RFI", "RFQ", "BA/DDS", "TSR",
              "ProjectNote", "ProjectName", "ProjectStatus", "Brand",
              "ProductLine", "ProductMode", "RFType", "RFSKU",
              "ProjectCode", "ProjectLeader", "Formfactor",
              "Main Location", "AUX Location", "ACover", "CCover", "DCover", "BOM"]
        now_timestamp = int(datetime.now().timestamp())
        now_iso = datetime.fromtimestamp(now_timestamp).isoformat()
        if not dict_project['RFQ']:
            logging.info("XXXXX Missing RFQ Date XXXXX")
            return JSONResponse(content={"Error": "No RFQ Date"}, status_code=400)
        if not dict_project['RFI']:
            logging.info("XXXXX Missing RFI Date XXXXX")
            return JSONResponse(content={"Error": "No RFI Date"}, status_code=400)
        rfq_timestamp = int(datetime.strptime(dict_project['RFQ'],"%Y-%m-%d").timestamp())
        rfi_timestamp = int(datetime.strptime(dict_project['RFI'],"%Y-%m-%d").timestamp())
        # 設定 RFQ -21 Days Due Day(as dd)
        dd = datetime.fromtimestamp(rfq_timestamp - 21*24*3600).isoformat()
        logging.info("Check Project Info ...")
        # 檢查 是現在時間是否於 DD day 之後
        check_rfq_due_day = now_iso >= dd
        dict_project['Light_of_pj_info'] = "green"
        missing_fields = []
        for key in check_key:
            if key not in dict_project:
                missing_fields.append(key)
                continue
            if dict_project[key]:
                continue
            if np.isnan(dict_project[key]):
                dict_project[key] = ""
            dict_project['Light_of_pj_info'] = "red" if check_rfq_due_day else "yellow"
            break
        if missing_fields:
            logging.info(f"Missing key : {missing_fields}")
            return JSONResponse(content={"Error": f"Missing key : {missing_fields}"}, status_code=400)
        logging.info(f"Set Light_of_pj_info -> {dict_project['Light_of_pj_info']}")
        # 設定t_start 時間點，為何如此設定，請問PO
        t_start = datetime.fromtimestamp(rfq_timestamp - (rfq_timestamp - rfi_timestamp)/2).isoformat()
        logging.info(f"Set t_start = {t_start}, Due day = {dd}")
        # 防止 dd 小於 t_start，要維持 dd >= t_start(timestamp)
        dd_switch = dd
        if dd <= t_start:
            dd_switch,t_start = t_start,dd_switch 
        logging.info("Checking request form light ...")
        dict_project['Light_of_request_form'] = check_request_form_light(list_request_form,now_iso,t_start,dd_switch)
        logging.info(f"Set Light_of_request_form -> {dict_project['Light_of_request_form']}")
        logging.info("Checking accept request form light ...")
        dict_project['Light_of_accept_request'] = check_accept_request_light(list_request_form)
        logging.info(f"Set Light_of_accept_request -> {dict_project['Light_of_accept_request']}")
        logging.info("Checking simulation result light ...")
        dict_project['Light_of_simulation_finished'] = check_sim_finished_light(list_request_form,now_iso,dict_project["Light_of_accept_request"])
        logging.info(f"Set Light_of_simulation_finished -> {dict_project['Light_of_simulation_finished']}")
        logging.info("Checking Status ...")
        dict_project['Status'] = check_status(dict_project)
        logging.info(f"Set Status -> {dict_project['Status']}")
        dict_project['Current_stage'],dict_project['Light_overall'] = check_overall(dict_project)
        logging.info(f"Set Stage -> {dict_project['Current_stage']}")
        res = project_list_col.update_one({"ProjectId": project_id},
                                    {"$set":dict_project})
        dict_respond={
            "project":dict_project,
            "request_form":list_request_form,
            "records":list_record
        }
        if res.acknowledged and res.matched_count > 0:
            logging.info(f"{project_id=} Updated Overall Status Successfully.")
            return JSONResponse(content=dict_respond, status_code=200)
        else:
            logging.info(f"{project_id=} Updated Overall Status Failed!!!")
            return JSONResponse(content={"Error": f"{project_id=} Updated Overall Status Failed."}, status_code=400)
    except NameError as e:
        logging.error(str(e))
        return JSONResponse(content={"Error": str(e)}, status_code=400)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")
    finally:
        if conn1:
            conn1.close()
        if conn2:
            conn2.close()
        if conn3:
            conn3.close()

@app.post("/data/cancel_overall_status")
def cancel_overall_status(eid: str,name: str,project_id: str,reason: str,csrf_validated=Depends(verify_csrf_token)):
    """Onwer 或 Admin Cacnel 整個案子的模擬。
    Args:
        eid (str): 員工工號.
        name (str): 員工英文名字.
        project_id (str): ProjectId.
        reason (str): Cancel reason.
        csrf_validated (_type_, optional): CSRF protect, Defaults to Depends(verify_csrf_token).

    Raises:
        Error Message: {"Error": f"{project_id=} Cancelled Failed!"},400
        Error Message: {"Error": "Cancel Reason Cannot Be Empty!!!"},400
        HTTPException: Any unexpected error.500, INTERNAL_ERROR to Web.

    Returns:
        dict: {"Message":f"{project_id=} Cancelled."},200
    """    
    conn1 = None
    try:
        logging.info(f"Get {project_id=}")
        conn1,project_list_col=connect_mongodb("RFSimulationRequest",db_pj_list)
        dict_project = project_list_col.find_one({"ProjectId":project_id},{"_id": 0})
        if not dict_project:
            logging.info(f"{project_id} Project Didn't In DB!!!")
            return JSONResponse(content={"Error": f"{project_id} Project Didn't In DB!!!"}, status_code=400)
        if not reason:
            logging.info(f"{project_id} Cancel Reason Cannot Be Empty!!!")
            return JSONResponse(content={"Error": "Cancel Reason Cannot Be Empty!!!"}, status_code=400)
        res = project_list_col.update_one({"ProjectId": project_id},
                                    {"$set":{"Status":"Cancelled",
                                             "Cancel_reason":reason
                                             }})
        
        if res.acknowledged and res.matched_count > 0:
            logging.info(f"{project_id=} Cancelled.")
            now_iso = datetime.now().isoformat()
            save_to_record(eid,name,'Cancel_Overall',project_id, "", now_iso)
            return JSONResponse(content={"Message":f"{project_id=} Cancelled."}, status_code=200)
        else:
            logging.info(f"{project_id=} Cancelled Failed!")
            return JSONResponse(content={"Error": f"{project_id=} Cancelled Failed!"}, status_code=400)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")
    finally:
        if conn1:
            conn1.close()

def check_request_form_light(list_request_form:list,now_iso:str,t_start:str,dd:str)-> str:
    try:
        # 已經做過模擬後，第二單以上皆為綠燈
        if len(list_request_form) > 1:
            logging.info(f"{len(list_request_form)} requests -> green.")
            return "green"
        # 1. 先判斷時間點 t_start > now -> 1, t_start <= now < dd  -> 2, now >= dd -> 3
        judge_timing = 2
        if t_start > now_iso:
            judge_timing = 1
        elif dd <= now_iso:
            judge_timing = 3
        logging.info(f"Get timing :{judge_timing} .")
        ## 判斷 0 reuqest
        if not list_request_form:
            if judge_timing == 1:
                logging.info("form_id: None -> gray.")
                return "gray"
            elif  judge_timing == 2:
                logging.info("form_id: None -> yellow.")
                return "yellow"
            else:
                logging.info("form_id: None -> red.")
                return "red"
        #? 針對第一單 request form 處理
        # 2. 綠燈情況為 reuqest form['request_status']=="Accept"
        item = list_request_form[0]
        logging.info(f"Get form_id: {item['form_id']} .")
        if item['request_status'] in ["Apply","Accept"]:
            logging.info(f"form_id: {item['form_id']} - request_status: {item['request_status']} -> green.")
            return "green"
        
        # 3. 判斷灰/黃/紅
        if item["request_status"] == "Reject":
            if judge_timing == 1:
                logging.info(f"form_id: {item['form_id']} - request_status: {item['request_status']} -> gray.")
                return "gray"
            elif  judge_timing == 2:
                logging.info(f"form_id: {item['form_id']} - request_status: {item['request_status']} -> yellow.")
                return "yellow"
            else:
                logging.info(f"form_id: {item['form_id']} - request_status: {item['request_status']} -> red.")
                return "red"
        return "green"
    except Exception as _:
        logging.error(f"XXXXX Error when checking request light:\n{traceback.format_exc()} XXXXX")
        raise NameError("Error_In_Checking_Request_Light")

def check_accept_request_light(list_request_form:list)->str:
    try:
        def check_apply_situation(item):
            now_timestamp = int(datetime.now().timestamp())
            create_time_stamp = int(datetime.fromisoformat(item['create_time']).timestamp())
            if now_timestamp - create_time_stamp >= 3*24*3600:
                logging.info(f"form_id: {item['form_id']} - request_status: {item['request_status']} Is Idle Up To 3 Days -> red.")
                return "red"
            logging.info(f"form_id: {item['form_id']} - request_status: {item['request_status']} Is Idle In 3 Days -> yellow.")
            return "yellow"
        ## 判斷 0 reuqest
        if not list_request_form:
            logging.info("0 Request To Accept -> gray.")
            return "gray"
        item = list_request_form[0]
        logging.info(f"Get form_id: {item['form_id']} .")
        # 第二單開始，若為 apply ，則 accept light 為黃色，若超過 create_time 3天還未 accept/reject 則紅色。
        # 已被 accept/reject/cancelled 則設綠色
        if len(list_request_form) > 1:
            if item['request_status'] == "Apply":
                return check_apply_situation(item)
            logging.info(f"form_id: {item['form_id']} - request_status: {item['request_status']} -> green.")
            return "green"
        #? 針對第一單 request form 處理
        # 1. 當 reuqest form['request_status'] in ["Accept","Finish"] 則設綠燈
        if item['request_status'] in ["Accept","Finish"]:
            logging.info(f"form_id: {item['form_id']} - request_status: {item['request_status']} -> green.")
            return "green"
        # 2. 當 reuqest form['request_status']=="apply"，是否超過 create_time 3天，未超過則黃，反之，紅
        if item['request_status'] == "Apply":
            return check_apply_situation(item)
        # 3. 其他情況皆為灰色
        logging.info(f"form_id: {item['form_id']} - request_status: {item['request_status']} -> gray.")
        return "gray"
    except Exception as _:
        logging.error(f"XXXXX Error when checking accept request light:\n{traceback.format_exc()} XXXXX")
        raise NameError("Error_In_Checking_Accept_Request_Light")

def check_sim_finished_light(list_request_form:list,now_iso:str,light_of_accept_request:str)->str:
    try:
        # light_of_accept_request 不是綠燈，則light_of_accept_request設為灰燈
        if light_of_accept_request != 'green':
            logging.info("Light_of_accept_request isn't green.")
            return 'gray'
        item = list_request_form[0]
        logging.info(f"Get form_id: {item['form_id']} .")
        # 上傳結果完成，request form 會有upload_date，light_of_accept_request 設為綠燈
        if "upload_date" in item:
            logging.info(f"form_id: {item['form_id']} - upload_date: {item['upload_date']} -> green.")
            return 'green'
        if item['request_status'] =='Reject' and len(list_request_form) > 1:
            logging.info(f"form_id: {item['form_id']} was rejected !!!")
            logging.info("Choose gray for Light_of_simulation_finished !!!")
            return 'green'
        due_day = datetime.strptime(item['due_date'], "%Y-%m-%d").isoformat()
        # 若為DD後仍未完成simulation result上傳則是紅色，反之，黃色
        logging.info(f"Set now = {now_iso}, Due day = {due_day}")
        return 'red' if now_iso >= due_day else 'yellow'
    except Exception as _:
        logging.error(f"XXXXX Error when checking simulation finished light:\n{traceback.format_exc()} XXXXX")
        raise NameError("Error_In_Checking_Simulation_Finished_Light")

def check_status(dict_project:dict)->str:
    try:
        timestep_tsr = int(datetime.strptime(dict_project['TSR'],"%Y-%m-%d").timestamp())
        now_timestamp = int(datetime.now().timestamp())
        if "Status" not in dict_project or now_timestamp <= timestep_tsr:
            return "On-going"
        if dict_project['Status']=="Cancelled":
            return "Cancelled"
        set_lights =set([dict_project['Light_of_pj_info'],
                        dict_project['Light_of_request_form'],
                        dict_project['Light_of_accept_request'],
                        dict_project['Light_of_simulation_finished']]
                        )
        if len(set_lights) == 1 and 'green' in set_lights:
            return "Finished"
        return "On-going"
    except Exception as _:
        logging.error(f"XXXXXcheck_status Error : \n{traceback.format_exc()} XXXXX")
        raise NameError("check_status Error")

def check_overall(dict_project:dict)->Tuple[str,str]:
    four_lights =[dict_project['Light_of_pj_info'],
                dict_project['Light_of_request_form'],
                dict_project['Light_of_accept_request'],
                dict_project['Light_of_simulation_finished']]
    
    four_stage=["Project Info","Request Form","Accept","Simulation"]
    current_stage ="Project Info"
    overall_light = "yellow"
    for idx, light in enumerate(four_lights):
        if light in ["red","yellow"]:
            current_stage = four_stage[idx]
            overall_light = light
            return current_stage,overall_light
        if light == 'gray':
            return current_stage,overall_light
        current_stage = four_stage[idx]
        overall_light = light

    if len(set(four_lights)) == 1 and 'green' in four_lights:
        return "Simulation","green"
    logging.error(f"XXXXX Can Not Judge Overall -> four lights {four_lights} XXXXX")
    raise NameError(f"XXXXX Can Not Judge Overall -> four lights {four_lights} XXXXX")
        
# ====================================================================================================== #
# --------------------------------------- API for Request form -------------------------------------- #
@app.post("/data/send_request_form")
def send_request_form(data: dict=Body(...),csrf_validated=Depends(verify_csrf_token)):
    """
        具有兩個功能, apply 和 update request form, 判斷方式為檢察 request "data" 中是否有 "form_id".
        必要攜帶內容: "ProjectId","Name","eID","antennas","3d_drawing_link","3d_drawing_password","solution_list","design_verify","me_design_verify"
        1. apply -> without the key "form_id" in request
        2. update -> with the key "form_id" in request
    Args:
        json_data (str): A string with json data from fornt-end
        csrf_validated (str, optional): Defaults to Depends(verify_csrf_token).

    Raises:
        Error Message: {"Error": "Permission Denied Data"},400
        ValueError: f"Missing {key}!"
        ValueError: f"Missing {key} Content!"
        ValueError: "Solution list Uploaded Failed! Please upload again!"
        ValueError: f"Apply failed: {dict_request}"
        ValueError: f"{form_id=} Updated Failed!"
        ValueError: f"{form_id=} Had Finished Simulation, Do Not Update This Request."
        Error Message: {""Error": str(ValueError)},400
        HTTPException: 500, INTERNAL_ERROR for unexpected error.

    Returns:
        json: 200,{"Message": "Apply Successfully!"} or {"Message":"'form_id' Updated."}
    """    
    conn2 = None
    try:
        check_key = ["ProjectId","Name","eID","antennas","3d_drawing_link","3d_drawing_password","solution_list","design_verify","me_design_verify"]
        for key in check_key :
            if key not in data:
                raise ValueError(f"Missing {key}!")
            if not data[key]:
                raise ValueError(f"Missing {key} Content!")
        if len(data.keys()) >len(check_key)+1:
            return JSONResponse(content={"Error": "Permission Denied Data"}, status_code=400)
        conn2,request_form_col=connect_mongodb("RFSimulationRequest",request_form)
        dict_request = {
                        "antennas":data['antennas'],
                        "3d_drawing_link":data['3d_drawing_link'],
                        "3d_drawing_password":data['3d_drawing_password'],
                        "solution_list":data['solution_list'],
                        "design_verify":data['design_verify'],
                        "me_design_verify":data['me_design_verify']}
        eid = data['eID']
        name = data['Name']
        project_id = data['ProjectId']
        iso_now = datetime.now().isoformat()
        logging.info(f"Get eID {eid} Send Request-> Project ID: {project_id}")
        logging.info(f"Get reuqest {dict_request}")
        #? 判斷 request 中，是否有 form_id，如果沒有表示為新的 apply
        #? 存在 form_id，則以舊單 update
        if "form_id" not in data :
            logging.info("New Request!!!")
            form_id = create_form_id(request_form_col)
            dict_request['form_id'] = form_id
            dict_request['ProjectId'] = project_id
            # 所有狀態 Apply/Accept/Reject/Finish
            dict_request['request_status'] = 'Apply'
            dict_request['create_time'] = iso_now
            logging.info(f"Apply Data Form_id : {form_id}")
            temp_sol_list = os.path.join(os.getcwd(), "FilesUpload", "temp", dict_request['solution_list'])
            if not os.path.exists(temp_sol_list):
                raise ValueError("Solution list Uploaded Failed! Please upload again!")
            destination_sol_list = os.path.join(os.getcwd(), "FilesUpload", form_id, "solution_list")
            os.makedirs(destination_sol_list, exist_ok=True)
            logging.info(f"Copy: {temp_sol_list} -> {destination_sol_list}")
            shutil.copy2(temp_sol_list, destination_sol_list)
            os.remove(temp_sol_list)
            logging.info("Done")
            logging.info("Insert data to DB")
            res = request_form_col.insert_one(dict_request)
            if res.acknowledged and res.inserted_id:
                logging.info(f"Apply successfully: {dict_request}")
                save_to_record(eid,name,'Apply',project_id, form_id, iso_now)
                return JSONResponse(content={"Message": "Apply Successfully!"}, status_code=200)
            logging.error(f"Apply failed: {dict_request}")
            raise ValueError(f"Apply failed: {dict_request}")
        else:
            logging.info("Old Request!!!")
            form_id = data['form_id']
            dict_chcek_status = request_form_col.find_one({"form_id":form_id})
            if dict_chcek_status['request_status'] == "Finish":
                raise ValueError(f"{form_id=} Had Finished Simulation, Do Not Update This Request.")
            temp_sol_list = os.path.join(os.getcwd(), "FilesUpload", "temp", dict_request['solution_list'])
            destination_sol_list = os.path.join(os.getcwd(), "FilesUpload", form_id, "solution_list", dict_request['solution_list'])
            if not os.path.exists(destination_sol_list):
                if not os.path.exists(temp_sol_list):
                    raise ValueError("Solution list Updated Failed! Please upload again!")
                logging.info(f"Copy: {temp_sol_list} -> {destination_sol_list}")
                shutil.copy2(temp_sol_list, destination_sol_list)
                os.remove(temp_sol_list)
                logging.info("Done")
            dict_request['request_status'] = "Apply"
            logging.info(f"Set {form_id=} request_status : Apply")
            res = request_form_col.update_one({"form_id":form_id},{"$set":dict_request})
            if res.acknowledged and res.matched_count > 0:
                logging.info(f"{form_id=} Updated.")
                save_to_record(eid,name,'Update',project_id, form_id, iso_now)
                return JSONResponse(content={"Message":f"{form_id=} Updated."}, status_code=200)
            logging.info(f"{form_id=} Updated Failed!")
            raise ValueError(f"{form_id=} Updated Failed!")
    except ValueError as e:
        logging.error(traceback.format_exc())
        return JSONResponse(content={"Error": str(e)}, status_code=400)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")
    finally:
        if conn2:
            conn2.close()

@app.post("/data/upload_solution_list")
async def upload_solution_list(file: UploadFile = File(...),csrf_validated=Depends(verify_csrf_token)):
    """上傳 request 需要的 Solution_list(可能是 excel 或是 ppt), 會先 call 此 API 進行暫存至 temp 資料夾中, 等待填寫完內容才會call "send_request_form".

    Args:
        file (UploadFile, optional): 上傳 request 需要的 Solution_list(可能是 excel 或是 ppt). Defaults to File(...).
        csrf_validated (_type_, optional): CSRF protect, Defaults to Depends(verify_csrf_token).

    Raises:
        Error Message: {"Error": f"Uploaded {file.filename} Failed! Again Please..."},400
        HTTPException: 500, INTERNAL_ERROR for unexpected error.

    Returns:
        dict: {"file": filename},200
    """    
    try:
        # 建立 temp 資料夾
        store_path = os.path.join(os.getcwd(), UPLOAD_FOLDER, "temp")
        os.makedirs(store_path, exist_ok=True)

        # 檔案原名
        filename = file.filename
        file_path = os.path.join(store_path, filename)

        # 如果檔名重複，加 uuid
        if os.path.exists(file_path):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(store_path, filename)

        # 儲存檔案
        file_content = await file.read()
        with open(file_path, "wb") as f:
            f.write(file_content)
        if not os.path.exists(file_path):
            return JSONResponse(content={"Error": f"Uploaded {file.filename} Failed! Again Please..."}, status_code=400)

        return JSONResponse(content={"file": filename}, status_code=200)
    except HTTPException as e:
        return JSONResponse(content={"Error": e}, status_code=403)
    except Exception:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")

@app.get("/download_solution_list/{form_id}/{filename}")
async def download_solution_list(form_id: str, filename: str):
    """成功 apply request form 後, 提供 admin 下載 solution list 檔案.

    Args:
        form_id (str): request form_id, 唯一，不能重複.
        filename (str): 要下載檔案的全名，需要包含副檔名。
        csrf_validated (_type_, optional): CSRF protect, Defaults to Depends(verify_csrf_token).

    Raises:
        Error Message: {"Error": "Solution List Cannot Be Found"},400
        HTTPException: 500, INTERNAL_ERROR for unexpected error.

    Returns:
        Download url: str.
    """    
    try:
        en_filename = urllib.parse.unquote(filename)
        logging.info(f"decode {filename=} -> {en_filename}")
        file_path = os.path.join(os.getcwd(), UPLOAD_FOLDER, form_id, "solution_list", en_filename)
        if not os.path.exists(file_path):
            return JSONResponse(content={"Error": "Solution List Cannot Be Found"}, status_code=400)

        # 根據副檔名設定 media_type
        ext = os.path.splitext(en_filename)[1].lower()
        if ext == ".xlsx":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif ext == ".xls":
            media_type = "application/vnd.ms-excel"
        elif ext == ".pptx":
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif ext == ".ppt":
            media_type = "application/vnd.ms-powerpoint"
        else:
            media_type = "application/octet-stream"  # 預設二進位檔案

        return FileResponse(file_path, media_type=media_type, filename=en_filename)

    except Exception:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")

@app.delete("/delete_solution_list/{filename}")
async def delete_solution_list(filename: str):
    """填寫 request form 上傳 solution list後, 給予刪除功能再度上傳.

    Args:
        filename (str): _description_

    Raises:
        Error Message: {"Error": "Solution List Cannot Be Found"},400
        HTTPException: 500, INTERNAL_ERROR for unexpected error.

    Returns:
        dict: {"Message": f"{filename} deleted successfully"}},200
    """    
    try:
        en_filename = urllib.parse.unquote(filename)
        logging.info(f"decode {filename=} -> {en_filename}")
        file_path = os.path.join(os.getcwd(), UPLOAD_FOLDER, "temp", en_filename)
        if not os.path.exists(file_path):
            return JSONResponse(content={"Error": "Solution List Cannot Be Found"}, status_code=400)
        os.remove(file_path)
        return JSONResponse(content={"Message": f"{en_filename} deleted successfully"}, status_code=200)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")

@app.post("/data/accept")
def accept(form_id:str,name:str,eid:str,due_date:str,csrf_validated=Depends(verify_csrf_token)):
    """提供 Admin Accept request form.

    Args:
        form_id (str): request form id.
        name (str): 員工英文名字.
        eid (str): 員工工號.
        due_date (str): Admin 設定的模擬到期日.
        csrf_validated (_type_, optional): CSRF protect. Defaults to Depends(verify_csrf_token).

    Raises:
        ValueError: "Permission Denied to Accept!"
        ValueError: f"No Request Form: {form_id=}"
        ValueError: f"{form_id=} Accepted Failed!"
        Error Message: {"Error": str(ValueError)},400
        HTTPException: 500, INTERNAL_ERROR for unexpected error.

    Returns:
        dict: {"Message":f"{form_id=} Accepted."},200
    """    
    conn2 = None
    try:
        if get_role(eid).upper() != "ADMIN":
            raise ValueError("Permission Denied to Accept!")
        conn2,request_form_col=connect_mongodb("RFSimulationRequest",request_form)
        dict_project = request_form_col.find_one({"form_id":form_id})
        if not dict_project:
            logging.info(f"No Request Form: {form_id=}")
            raise ValueError(f"No Request Form: {form_id=}")
        project_id = dict_project["ProjectId"]
        now_iso = datetime.now().isoformat()
        dict_request={
            "request_status":"Accept",
            "accept_date":now_iso,
            "due_date":due_date
            }
        res = request_form_col.update_one({"form_id":form_id},
                                          {"$set":dict_request})
        if res.acknowledged and res.matched_count > 0:
            logging.info(f"{form_id=} Accepted.")
            save_to_record(eid,name,'Accept',project_id, form_id, now_iso)
            return JSONResponse(content={"Message":f"{form_id=} Accepted."}, status_code=200)
        logging.info(f"{form_id=} Accepted Failed!")
        raise ValueError(f"{form_id=} Accepted Failed!")
    except ValueError as e:
        logging.error(traceback.format_exc())
        return JSONResponse(content={"Error": str(e)}, status_code=400)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")
    finally:
        if conn2:
            conn2.close()

@app.post("/data/reject")
def reject(form_id:str,name:str,eid:str,reason:str,csrf_validated=Depends(verify_csrf_token)):
    """提供 Admin Reject request form

    Args:
        form_id (str): request form id.
        name (str): 員工英文名字.
        eid (str): 員工工號.
        reason (str): Reject reason.
        csrf_validated (_type_, optional): CSRF protect, Defaults to Depends(verify_csrf_token).

    Raises:
        ValueError: "Permission Denied to Reject!"
        ValueError: f"No Request Form: {form_id=}"
        ValueError: f"{form_id=} Rejected Failed!"
        Error Message: {"Error": str(ValueError)},400
        HTTPException: 500, INTERNAL_ERROR for unexpected error.

    Returns:
        dict: {"Message":f"{form_id=} Rejected."},200
    """    
    try:
        if get_role(eid).upper() != "ADMIN":
            raise ValueError("Permission Denied to Reject!")
        conn2 = None
        conn2,request_form_col=connect_mongodb("RFSimulationRequest",request_form)
        dict_project = request_form_col.find_one({"form_id":form_id})
        if not dict_project:
            logging.info(f"No Request Form: {form_id=}")
            raise ValueError(f"No Request Form: {form_id=}")
        project_id = dict_project["ProjectId"]
        now_iso = datetime.now().isoformat()
        dict_request={
            "request_status":"Reject",
            "reason":reason
            }
        res = request_form_col.update_one({"form_id":form_id},
                                          {"$set":dict_request})
        if res.acknowledged and res.matched_count > 0:
            logging.info(f"{form_id=} Rejected.")
            save_to_record(eid,name,'Reject',project_id, form_id, now_iso)
            return JSONResponse(content={"Message":f"{form_id=} Rejected."}, status_code=200)
        logging.info(f"{form_id=} Rejected Failed!")
        raise ValueError(f"{form_id=} Rejected Failed!")
    except ValueError as e:
        logging.error(str(e))
        return JSONResponse(content={"Error": str(e)}, status_code=400)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")
    finally:
        if conn2:
            conn2.close()

# ====================================================================================================== #
# ---------------------------- API for Result Part ----------------------------- #
@app.post("/data/finished_request")
def finished_request(form_id:str,name:str,eid:str,kpi:dict,solution_pdf_name:str,result_pdf_name:str,image_list:list=Body(...),csrf_validated=Depends(verify_csrf_token)):
    """由 Admin 填寫 Result 上傳模擬結果,Finish request form.

    Args:
        form_id (str): request form id.
        name (str): 員工英文名字.
        eid (str): 員工工號.
        kpi (dict): 由 Admin 上傳時提供,模擬數值kpi比較.
        solution_pdf_name (str): 模擬的solution list file name(pdf).
        result_pdf_name (str): 模擬的result file name(pdf).
        image_list (list, optional): 模擬的result png file name. Defaults to Body(...).
        csrf_validated (_type_, optional): CSRF protect. Defaults to Depends(verify_csrf_token).

    Raises:
        ValueError: "form_id Cannot Be Empty!"
        ValueError: "name Cannot Be Empty!"
        ValueError: "eid Cannot Be Empty!"
        ValueError: "kpi Cannot Be Empty!"
        ValueError: "Solution List Cannot Be Empty!"
        ValueError: "Simulation Result Cannot Be Empty!"
        ValueError: "Me images Cannot Be Empty!"
        ValueError: f"No Request Form: {form_id=}"
        ValueError: "Permission Denied Data"
        ValueError: f"{form_id=} Finished Failed!"
        ValueError: f"{form_id=} Finished Failed!"
        Error Message: {"Error": str(ValueError)},400
        HTTPException: 500, INTERNAL_ERROR for unexpected error.

    Returns:
        dict: {"Message":f"{form_id=} Finished."},200
    """    
    conn2 = None
    try:
        if get_role(eid).upper() != "ADMIN":
            raise ValueError("Permission Denied to Finish Request!")
        if not form_id:
            raise ValueError(status_code=400, detail="form_id Cannot Be Empty!")
        if not name:
            raise ValueError(status_code=400, detail="name Cannot Be Empty!")
        if not eid:
            raise ValueError(status_code=400, detail="eid Cannot Be Empty!")
        if not kpi:
            raise ValueError(status_code=400, detail="kpi Cannot Be Empty!")
        if not solution_pdf_name:
            raise ValueError(status_code=400, detail="Solution List Cannot Be Empty!")
        if not result_pdf_name:
            raise ValueError(status_code=400, detail="Simulation Result Cannot Be Empty!")
        if not image_list:
            raise ValueError(status_code=400, detail="Me images Cannot Be Empty!")
        conn2,request_form_col=connect_mongodb("RFSimulationRequest",request_form)
        dict_project = request_form_col.find_one({"form_id":form_id})
        if not dict_project:
            logging.info(f"No Request Form: {form_id=}")
            raise ValueError(f"No Request Form: {form_id=}")
        check_kpi = ["me_solution_compare","cost_compare","num_me_position_compare","me_index_compare"]
        if len(kpi) != len(check_kpi):
            logging.info(f"Wrong KPI data: {kpi}")
            raise ValueError("Permission Denied Data")
        project_id = dict_project["ProjectId"]
        now_iso = datetime.now().isoformat()
        dict_request={
            "request_status":"Finish",
            "solution_pdf_name":solution_pdf_name,
            "result_pdf_name": result_pdf_name,
            "result_image":image_list,
            "upload_date":now_iso,
            "kpi":kpi
            }
        res = request_form_col.update_one({"form_id":form_id},
                                          {"$set":dict_request})
        if res.acknowledged and res.matched_count > 0:
            logging.info(f"{form_id=} Finished.")
            save_to_record(eid,name,'Finish',project_id, form_id, now_iso)
            return JSONResponse(content={"Message":f"{form_id=} Finished."}, status_code=200)
        logging.info(f"{form_id=} Finished Failed!")
        raise ValueError(f"{form_id=} Finished Failed!")
    except ValueError as e:
        logging.error(str(e))
        return JSONResponse(content={"Error": str(e)}, status_code=400)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")
    finally:
        if conn2:
            conn2.close()

@app.post("/data/upload_pdf_result")
async def upload_pdf_result(form_id:str, file:str , pdf: UploadFile = File(...) ,csrf_validated=Depends(verify_csrf_token)):
    """上傳 result 的兩種 pdf, solution_list/ simulation result.
    file 參數兩種: solution_list/ result.

    Args:
        form_id (str): request form id.
        file (str): 依照上傳結果, solution_list/ result.
        pdf (UploadFile, optional): 上傳 solution list 或 result pdf. Defaults to File(...).
        csrf_validated (_type_, optional): CSRF protect. Defaults to Depends(verify_csrf_token).

    Raises:
        HTTPException: 500, INTERNAL_ERROR for unexpected error.

    Returns:{
                "form_id": form_id,
                "download_url": download_url
            },200
    """    
    try:
        pdf_content = await pdf.read()

        # 建立存放目錄: FilesUpload/form_id/pdf
        store_path = os.path.join(os.getcwd(), UPLOAD_FOLDER, form_id, "pdf", file)
        shutil.rmtree(store_path, ignore_errors=True)
        os.makedirs(store_path, exist_ok=True)
        file_path = os.path.join(store_path, pdf.filename)

        # 儲存PDF檔案
        with open(file_path, "wb") as f:
            f.write(pdf_content)
        # URL encode filename
        encoded_filename = urllib.parse.quote(pdf.filename)

        download_url = f"/download_pdf/{form_id}/{file}/{encoded_filename}"

        return JSONResponse(
            content={
                "form_id": form_id,
                "download_url": download_url
            },
            status_code=200
        )
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")

# 提供PDF下載API, 給予 form_id 和 filename 由後端組成路徑，資安問題
@app.get("/download_pdf/{form_id}/{file}/{filename}")
async def download_pdf(form_id: str, file:str, filename: str):
    """給予前端預覽 pdf 功能.
    """    
    try:
        en_filename = urllib.parse.unquote(filename)
        logging.info(f"decode {filename=} -> {en_filename}")
        file_path = os.path.join(os.getcwd(), UPLOAD_FOLDER, form_id, "pdf", file, en_filename)
        if not os.path.exists(file_path):
            return JSONResponse(content={"Error": "PDF Cannot Be Found"}, status_code=400)
        headers = {
            "Content-Disposition": f'inline; filename="{en_filename}"'
        }
        return FileResponse(file_path, media_type="application/pdf", filename=en_filename, headers=headers)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")

@app.delete("/delete_pdf/{form_id}/{file}/{filename}")
async def delete_pdf(form_id: str, file: str, filename:str):
    """給予前端上傳錯誤時可以delete 再上傳.
    """    
    try:
        en_filename = urllib.parse.unquote(filename)
        logging.info(f"decode {filename=} -> {en_filename}")
        file_path = os.path.join(os.getcwd(), UPLOAD_FOLDER, form_id, "pdf", file, en_filename)
        if not os.path.exists(file_path):
            return JSONResponse(content={"Error": "PDF Cannot Be Found"}, status_code=400)
        os.remove(file_path)
        return JSONResponse(content={"Message": f"{en_filename} deleted successfully"}, status_code=200)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")

@app.post("/data/upload_plot_result")
async def upload_plot_result(form_id: str,images: List[UploadFile] = File(...),csrf_validated=Depends(verify_csrf_token)):
    """由 Admin 上傳 result plot.

    Args:
        form_id (str): request form id.
        images (List[UploadFile], optional): result plot, 只接受 "jpg"/"jpeg"/"png". Defaults to File(...).
        csrf_validated (_type_, optional): CSRF protect. Defaults to Depends(verify_csrf_token).

    Raises:
        HTTPException: 500, INTERNAL_ERROR for unexpected error.

    Returns:
        dict: {
                "form_id": form_id,
                "download_urls": download_urls
            },200
    """    
    try:
        store_path = os.path.join(os.getcwd(), UPLOAD_FOLDER, form_id, 'plot')
        shutil.rmtree(store_path, ignore_errors=True)
        os.makedirs(store_path, exist_ok=True)
        download_urls = []
        ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}
        ALLOWED_EXTS = {".png", ".jpg", ".jpeg"}
        for img in images:
            ext = os.path.splitext(img.filename)[1].lower()
            if ext not in ALLOWED_EXTS or img.content_type not in ALLOWED_IMAGE_TYPES:
                return JSONResponse(content={"Error": f"Invalid image type: {img.filename}"}, status_code=400)
            img_content = await img.read()
            img_path = os.path.join(store_path, img.filename)
            with open(img_path, "wb") as f:
                f.write(img_content)
            encoded_filename = urllib.parse.quote(img.filename)
            download_url = f"/download_plot/{form_id}/{encoded_filename}"
            download_urls.append(download_url)

        return JSONResponse(
            content={
                "form_id": form_id,
                "download_urls": download_urls
            },
            status_code=200
        )
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")

@app.get("/download_plot/{form_id}/{filename}")
async def download_plot(form_id: str, filename: str):
    """提供給前端預覽plot功能.
    """    
    try:
        en_filename = urllib.parse.unquote(filename)
        logging.info(f"decode {filename=} -> {en_filename}")
        safe_form_id = os.path.basename(form_id)
        safe_filename = os.path.basename(en_filename)
        file_path = os.path.join(os.getcwd(), UPLOAD_FOLDER, safe_form_id, 'plot', safe_filename)
        if not os.path.exists(file_path):
            return JSONResponse(content={"Error": "Plot Cannot Be Found"}, status_code=400)
        ext = os.path.splitext(safe_filename)[-1].lower()
        if ext == ".png":
            media_type = "image/png"
        elif ext in [".jpg", ".jpeg"]:
            media_type = "image/jpeg"
        else:
            return JSONResponse(content={"Error": "Invalid image type"}, status_code=400)
        headers = {
            "Content-Disposition": f'inline; filename="{safe_filename}"'
        }
        return FileResponse(file_path, media_type=media_type, filename=safe_filename, headers=headers)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")

@app.delete("/delete_plot/{form_id}")
async def delete_plot(form_id: str):
    """給予前端上傳錯誤時可以delete 再上傳.會一次全部刪除 plot.
    """  
    try:
        safe_form_id = os.path.basename(form_id)
        file_path = os.path.join(os.getcwd(), UPLOAD_FOLDER, safe_form_id, 'plot')
        shutil.rmtree(file_path, ignore_errors=True)
        return JSONResponse(content={"Message": "Deleted successfully"}, status_code=200)
    except Exception as _:
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="INTERNAL_ERROR")
# ====================================================================================================== #
# ---------------------------- Functional API ----------------------------- #
@app.get("/data/get_role_list")
def get_role_list():
    """將 White list 提供給前端.
    """    
    conn4 = None 
    try:
        conn4,white_list_col=connect_mongodb("RFSimulationRequest","white_list")
        list_role = list(white_list_col.find({},{"_id":0}))
        dict_request = {
            "role_list":list_role 
        }
        return JSONResponse(content = dict_request, status_code = 200)
    except Exception as ex:
        logging.error(traceback.format_exc())
        raise ValueError(f"Get Role Fail! {ex}")
    finally:
        if conn4:
            conn4.close()

@app.post("/data/check_role")
def check_role(eid:str,csrf_validated=Depends(verify_csrf_token)):
    """提供前端確認該 eID 的身分.
    """    
    conn4 = None 
    try:
        conn4,white_list_col=connect_mongodb("RFSimulationRequest","white_list")
        dict_person = white_list_col.find_one({"eID":eid})
        if dict_person :
            return JSONResponse(content={"Message":"Admin"}, status_code=200)
        return JSONResponse(content={"Message":"User"}, status_code=200)
    except Exception as ex:
        logging.error(traceback.format_exc())
        raise ValueError(f"Check Role Fail! {ex}")
    finally:
        if conn4:
            conn4.close()

@app.post("/data/set_role")
def set_role(name:str,eid:str,role:str,csrf_validated=Depends(verify_csrf_token)):
    """設定 eID 的身分.
    """    
    conn4 = None 
    try:
        logging.info(f"Get eID={eid}/ {name=}/ {role=}")
        conn4,white_list_col=connect_mongodb("RFSimulationRequest","white_list")
        dict_person = white_list_col.find_one({"eID":eid})
        if dict_person :
            return JSONResponse(content={"Message":f"Set eID={eid}- {name=}- {role=}"}, status_code=200)
        dict_request = {
            "name": name,
            "eID": eid,
            "role": role
        }
        res = white_list_col.insert_one(dict_request)
        if res.acknowledged and res.inserted_id:
            logging.info(f"Set eID={eid}/ {name=}/ {role=}")
            return JSONResponse(content={"Message":f"Set eID={eid}/ {name=}/ {role=}"}, status_code=200)

        logging.info(f"Set eID={eid}/ {name=}/ {role=} Failed!")
        raise ValueError(f"Set eID={eid}/ {name=}/ {role=} Failed!")
    except Exception as ex:
        logging.error(traceback.format_exc())
        raise ValueError(f"Set Role Fail! {ex}")
    finally:
        if conn4:
            conn4.close()

# DELETE：移除角色
@app.delete("/data/delete_role")
def delete_role(eid: str):
    """刪除 eID 的身分.
    """    
    conn4 = None
    try:
        logging.info(f"Get eID={eid}")
        conn4, white_list_col = connect_mongodb("RFSimulationRequest", "white_list")
        res = white_list_col.delete_one({"eID": eid})
        if res.acknowledged and res.deleted_count > 0:
            logging.info(f"Deleted role successfully for eID={eid}")
            return JSONResponse(content={"Message": f"Deleted role for eID={eid}"}, status_code=200)
        logging.error(f"Delete failed: eID={eid} not found")
        return JSONResponse(content={"Error": f"eID={eid} not found"}, status_code=400)
    except Exception as ex:
        logging.error(traceback.format_exc())
        return JSONResponse(content={"Error": f"Delete role failed: {ex}"}, status_code=500)
    finally:
        if conn4:
            conn4.close()

def create_form_id(request_form_col:Collection)-> str:
    try_times = 0
    while try_times < 6:
        now = datetime.now()
        now_timestamp = now.timestamp()
        form_id = (
            str(now.year) +
            f"{now.month:02d}" +
            f"{now.day:02d}" +
            '_' +
            str(int(now_timestamp * 1000))
        )
        if not request_form_col.find_one({"form_id": form_id}):
            return form_id
        time.sleep(0.001)  # 等1毫秒
        try_times += 1
    raise ValueError("XXXXX Create_form_id Keeps Overlaping, Please Send Again Later!XXXXX")

def save_to_record(eid:str, name:str, action:str, project_id:str, form_id:str,now_iso:str):
    conn3 = None  # 預設為 None，以防 finally 檢查時出錯
    try:
        # 假設 record 是 collection name 字串
        conn3, record_col = connect_mongodb("RFSimulationRequest", record)
        dict_record = {
            "eID": eid,
            "Name": name,
            "action": action,
            "ProjectId": project_id,
            "form_id": form_id,
            "time": now_iso
        }
        res = record_col.insert_one(dict_record)
        if res.acknowledged and res.inserted_id:
            logging.info(f"Record: {dict_record}")
        else:
            logging.error(f"Failed To Save Record: {dict_record}")
            raise ValueError(f"Failed To Save Record: {dict_record}")
    except Exception as ex:
        logging.error(traceback.format_exc())
        raise ValueError(f"Saved Record Fail! {ex}")
    finally:
        if conn3:
            conn3.close()

def get_role(eid:str)->str:
    """Searching whitelist for authentication with Accept/Reject

    Args:
        eid (str): eID for a employee

    Returns:
        str: user/ admin
    """  
    conn4 = None 
    try:
        conn4,white_list_col=connect_mongodb("RFSimulationRequest","white_list")
        dict_person = white_list_col.find_one({"eID":eid})
        if not dict_person :
            return "user"
        return dict_person['role']
    except Exception as ex:
        logging.error(traceback.format_exc())
        raise ValueError(f"Get Record Fail! {ex}")
    finally:
        if conn4:
            conn4.close()

# ---------- Connect to MongoDB ---------------------
def connect_mongodb(str_db_name, str_table_name):
    conn = MongoClient(
        db_url,
        username=MONGODB_USER,
        password=MONGODB_PASSWORD,
        authSource="admin",
        authMechanism="SCRAM-SHA-1"
    )
    db = conn[str_db_name]
    collect = db[str_table_name]
    return conn, collect
if __name__ == "__main__":
    port_num = 2520
    app.openapi = custom_openapi
    if is_product_env:
        uvicorn.run(
        "__main__:app",
        host="0.0.0.0",
        port=port_num,
        reload=True,
        ssl_keyfile=r"C:\inetpub\wistronIISCA\STAR_wistron.com.key",
        ssl_certfile=r"C:\inetpub\wistronIISCA\STAR_wistron.com.crt"
    )
    else:
        uvicorn.run("__main__:app",host="0.0.0.0",port=port_num,reload=True)
        