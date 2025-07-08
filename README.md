# RF Simulation Request API 文件

---

## 1. API 功能總覽

| 編號 | 功能說明                   | Path                                           |
|------|----------------------------|------------------------------------------------|
| 1.   | 查詢專案整體狀態           | [GET]    /data/update_overall_status/{project_id}     |
| 2.   | 取消專案模擬               | [POST]   /data/cancel_overall_status                   |
| 3.   | 新增/更新 request form     | [POST]   /data/send_request_form                       |
| 4.   | 上傳 solution list(暫存 temp 中)       | [POST]   /data/upload_solution_list                    |
| 5.   | 下載 solution list         | [GET]    /download_solution_list/{form_id}/{filename}  |
| 6.   | 刪除暫存 solution list     | [DELETE] /delete_solution_list/{filename}              |
| 7.   | Accept request form        | [POST]   /data/accept                                  |
| 8.   | Reject request form        | [POST]   /data/reject                                  |
| 9.   | 完成模擬結果               | [POST]   /data/finished_request                        |
| 10.  | 上傳模擬 PDF               | [POST]   /data/upload_pdf_result                       |
| 11.  | 下載/預覽 PDF              | [GET]    /download_pdf/{form_id}/{file}/{filename}     |
| 12.  | 刪除 PDF                   | [DELETE] /delete_pdf/{form_id}/{file}/{filename}       |
| 13.  | 上傳模擬圖片               | [POST]   /data/upload_plot_result                      |
| 14.  | 下載/預覽模擬圖片          | [GET]    /download_plot/{form_id}/{filename}           |
| 15.  | 刪除所有模擬圖片           | [DELETE] /delete_plot/{form_id}                        |
| 16.  | 取得角色白名單             | [GET]    /data/get_role_list                           |
| 17.  | 查詢 eID 身分              | [POST]   /data/check_role                              |
| 18.  | 新增/設定 eID 身分         | [POST]   /data/set_role                                |
| 19.  | 刪除 eID 身分              | [DELETE] /data/delete_role                             |

---

## 2. 共通說明

- 所有 POST 需帶 `X-CSRF-Token` header。
- 回傳皆為 JSON（或檔案下載）。
- 成功回傳 `status_code=200`，失敗依情況回傳 400/403/404/500。
- FastAPI docs: https://domain.com:"port"/docs

---

## 3. API 詳細說明

### 3.1 查詢專案整體狀態

- 路徑：[GET] /data/update_overall_status/{project_id}
- 描述：查詢指定 project_id 的專案資訊、request_form、歷史紀錄，並計算專案階段與燈號。
- request:
  - Content-Type: 無
  - request parameter:

  | 參數         | 型別 | 必填 | 說明         | 範例 |
  |--------------|------|------|--------------|------|
  | project_id   | str  | Y    | 專案ID       | r-cy25jarvisinspiron14_16-142in1wlansku |
- respond: `application/json`
- error message: 詳見下方
    ```json
        { "Error": "Missing Project: r-cy25jarvisinspiron14_16-142in1wlansku" }
        { "Error": "Missing Project: {project_id}" }`
        { "Error": "Duplicated ProjectID: {project_id}" }`
        { "Error": "No RFQ Date" }
        { "Error": "No RFI Date" }`
        { "Error": "Missing key : [...]" }`
        { "Error": "{project_id} Updated Overall Status Failed." }
        { "Error": ValueError Content }`
        { "detail": "INTERNAL_ERROR" }`
    ```
- sample  
  - request sample:  
    ```
    GET /data/update_overall_status/r-cy25jarvisinspiron14_16-142in1wlansku
    ```
  - respond sample:
    ```json
    {
      "project": {
        "ProjectNote": "R-CY25 JARVIS INSPIRON 14_16-142in1",
        "ACover": "Full metal",
        "AUX Location": "NB22_SYS_right_front",
        "BA/DDS": "2024-06-27",
        "BOM": [
          {
            "Category": "RF",
            "WistronPN": "434.0Q914.0001",
            "AsseblyParts": "MB 輔料",
            "Price": 0.0063,
            "TotalPrice": 0,
            "Qty": 1,
            "Size": "14*8.5*0.1",
            "Thickness": "0",
            "Item": "Al_Cu_Foil",
            "AppPos": "USB3.0",
            "Status": "Keep",
            "MERemark": "",
            "Remark": "",
            "Material": "單導銅_含一般(不導電)背膠",
            "MaterialSpec": "T0.1_AlCu",
            "RfMappingCode": 28,
            "MeDesignOpportunity": "",
            "MeDesignOpportunityComment": ""
          },
        ... more BOM items
        ],
        "Brand": "Rosa",
        "CCover": "Full metal",
        "DCover": "Full plastic",
        "Formfactor": "14",
        "MP": "2025-02-26",
        "Main Location": "NB18_SYS_left_front",
        "ProductLine": "Notebook.Computer",
        "ProductMode": "2-in-1",
        "ProjectCode": "QRQY00030675",
        "ProjectId": "r-cy25jarvisinspiron14_16-142in1wlansku",
        "ProjectLeader": "NICK KUO",
        "ProjectName": "R-CY25 JARVIS INSPIRON 14_16",
        "ProjectStatus": "Close",
        "RFI": "2024-03-20",
        "RFQ": "2024-05-28",
        "RFSKU": "WLAN SKU",
        "RFType": "3a",
        "TSR": "2001-05-30",
        "sim_due_date": "2024-06-20",
        "sim_start": "2024-06-06",
        "Status": "Finished",
        "Current_stage": "Simulation",
        "Light_of_accept_request": "green",
        "Light_of_pj_info": "green",
        "Light_of_request_form": "green",
        "Light_of_simulation_finished": "green",
        "Light_overall": "green"
      },
      "request_form": [
        {
          "antennas": [
            {
              "remark": "palm-rest",
              "antenna": "Main",
              "antennaLocation": [19, 20, 21],
              "details": [
                {
                  "internalizationPosition": "P1",
                  "importable": true,
                  "extensionPosition": "C件延伸",
                  "cGap": 1.2,
                  "dGap": null
                }
                ... more details
              ]
            },
            {
              "remark": "hinge-up",
              "antenna": "Aux",
              "antennaLocation": [6, 7, 8],
              "details": [
                {
                  "internalizationPosition": "L1",
                  "importable": null,
                  "extensionPosition": null,
                  "cGap": null,
                  "dGap": null
                }
                ...
              ]
            }
          ],
          "3d_drawing_link": "shareponit_link",
          "3d_drawing_password": "123",
          "solution_list": "solution_list_48dc44f2f0124e628bd1fedf9343e9f8.pdf",
          "design_verify": "Y",
          "me_design_verify": "N",
          "form_id": "20250630_1751271939265",
          "ProjectId": "r-cy25jarvisinspiron14_16-142in1wlansku",
          "request_status": "Reject",
          "create_time": 1751271939265,
          "reason": "888888888888888888777123123"
        },
        ... more request forms
      ],
      "records": [
        {
          "eID": "11010059",
          "Name": "Peter YH Chang",
          "action": "Reject",
          "form_id": "20250630_1751271939265",
          "time": 1751272089,
          "ProjectId": "r-cy25jarvisinspiron14_16-142in1wlansku"
        }
        ... more records
      ]
    }
    ```
  - error message 範例：
    ```json
    { "Error": "Missing Project: r-cy25jarvisinspiron14_16-142in1wlansku" }
    ```

---

### 3.2 取消專案模擬

- 路徑：[POST] /data/cancel_overall_status
- 描述：由 Owner 或 Admin 取消整個案子的模擬。
- request:
  - Content-Type: application/json
  - request parameter:

  | 參數       | 型別 | 必填 | 說明         | 範例        |
  |------------|------|------|--------------|-------------|
  | eid        | str  | Y    | 員工工號     | 11010059    |
  | name       | str  | Y    | 員工英文名字 | Peter YH Chang |
  | project_id | str  | Y    | ProjectId    | r-cy25jarvisinspiron14_16-142in1wlansku |
  | reason     | str  | Y    | 取消原因     | Project closed |

- respond: `application/json`
- error message:
    ```json
    { "Error": "project_id='xxx' Cancelled Failed!" }
    { "Error": "xxx Project Didn't In DB!!!" }
    {"Error": "Cancel Reason Cannot Be Empty!!!"}
    { "detail": "INTERNAL_ERROR" }
    ```
- sample  
  - request sample:
    ```json
    {
      "eid": "11010059",
      "name": "Peter YH Chang",
      "project_id": "r-cy25jarvisinspiron14_16-142in1wlansku",
      "reason": "Project closed"
    }
    ```
  - respond sample:
    ```json
    { "Message": "project_id='r-cy25jarvisinspiron14_16-142in1wlansku' Cancelled." }
    ```
  - error message:
    ```json
    { "Error": "project_id='xxx' Cancelled Failed!" }
    ```

---

### 3.3 新增/更新 request form

- 路徑：[POST] /data/send_request_form
- 描述：apply 或 update request form，需先上傳 solution_list
- request:
  - Content-Type: application/json
  - request parameter:

  | 參數                | 型別  | 必填 | 說明                        | 範例                   |
  |---------------------|-------|------|-----------------------------|------------------------|
  | ProjectId           | str   | Y    | 專案ID                      | r-cy25jarvisinspiron14_16-142in1wlansku |
  | Name                | str   | Y    | 員工英文名字                | Peter YH Chang         |
  | eID                 | str   | Y    | 員工工號                    | 11010059               |
  | antennas            | list  | Y    | 天線資訊                    | [ ... ]                |
  | 3d_drawing_link     | str   | Y    | sharepoint link             | shareponit_link        |
  | 3d_drawing_password | str   | Y    | sharepoint 密碼             | 123                    |
  | solution_list       | str   | Y    | solution list 檔案          | solution_list.pdf      |
  | design_verify       | str   | Y    | Y/N                         | Y                      |
  | me_design_verify    | str   | Y    | Y/N                         | N                      |
  | form_id             | str   | N    | request form id（更新必填） | 20250630_1751271939265 |

- respond: `application/json`
- error message:
    ```json
    {"Error": "Permission Denied Data" }
    { "Error": "Missing {key}!" }
    { "Error": "Missing {key} Content!" }
    { "Error": "Solution list Uploaded Failed! Please upload again!" }
    { "Error": "Apply failed: {request_data}" }
    { "Error": "form_id='xxx' Updated Failed!" }
    { "Error": "ValueError contnet" }
    { "detail": "INTERNAL_ERROR" }
    ```
- sample  
  - request sample: 
    ```json
    {
      "Name": "Peter YH Chang",
      "eID": "11010059",
      "ProjectId": "r-cy25jarvisinspiron14_16-142in1wlansku",
      "design_verify": "Y",
      "me_design_verify": "N",
      "3d_drawing_link": "shareponit_link",
      "3d_drawing_password": "123",
      "solution_list": "solution_list.pdf",
      "antennas": [{
            "remark": "palm-rest",
            "antenna": "Main",
            "antennaLocation": [19, 20, 21],
            "details": [
              {
                "internalizationPosition": "P1",
                "importable": true,
                "extensionPosition": "C件延伸",
                "cGap": 1.2,
                "dGap": null
              },
              ...
              {
                "internalizationPosition": "Others",
                "importable": null,
                "extensionPosition": null,
                "cGap": null,
                "dGap": null
              }
            ]
          },
          {
            "remark": "hinge-up",
            "antenna": "Aux",
            "antennaLocation": [6, 7, 8],
            "details": [
              {
                "internalizationPosition": "L1",
                "importable": null,
                "extensionPosition": null,
                "cGap": null,
                "dGap": null
              },
              ...
              {
                "internalizationPosition": "Others",
                "importable": null,
                "extensionPosition": null,
                "cGap": null,
                "dGap": null
              }
            ]
          }]
      // 如為更新，須加上 form_id
    }
    ```
  - respond sample:
    ```json
    { "Message": "Apply Successfully!" }
    ```
    ```json
    { "Message": "form_id='xxx' Updated." }
    ```
  - error message:
    ```json
    { "Error": "Missing {key}!" }
    ```

---

### 3.4 上傳 solution list

- 路徑：[POST] /data/upload_solution_list
- 描述：上傳 request 需要的 solution_list，支援 excel/ppt，上傳後暫存於 temp 資料夾
- request:
  - Content-Type: multipart/form-data
  - request body:
    | 參數 | 型別      | 說明              |
    |------|-----------|-------------------|
    | file | UploadFile| solution_list 檔案|

- respond: `application/json`
- error message: 詳見下方
- sample  
  - request sample:
    ```
    POST /data/upload_solution_list
    form-data: file=solution_list.xlsx
    ```
  - respond sample:
    ```json
    { "file": "solution_list.xlsx" }
    ```
  - error message:
    ```json
    { "Error": "Uploaded solution_list.xlsx Failed! Again Please..." }
    ```

---

### 3.5 下載 solution list

- 路徑：[GET] /download_solution_list/{form_id}/{filename}
- 描述：下載 solution_list 檔案
- request:
  - Content-Type: 無
  - request parameter:

  | 參數      | 型別 | 必填 | 說明             | 範例                   |
  |-----------|------|------|------------------|------------------------|
  | form_id   | str  | Y    | request form id  | 20250630_1751271939265 |
  | filename  | str  | Y    | 檔案名稱         | solution_list.xlsx     |

- respond: 檔案下載
- error message:
    ```json
    { "Error": "Solution List Cannot Be Found" }
    ```

---

### 3.6 刪除暫存 solution list

- 路徑：[DELETE] /delete_solution_list/{filename}
- 描述：刪除 temp 資料夾內的 solution_list
- request:
  - Content-Type: 無
  - request parameter:

  | 參數    | 型別 | 必填 | 說明              | 範例               |
  |---------|------|------|-------------------|--------------------|
  | filename| str  | Y    | solution_list 檔案| solution_list.xlsx |

- respond: `application/json`
- error message:
    ```json
    { "Error": "Solution List Cannot Be Found" }
    ```
- sample:
  - request sample:
    ```
    DELETE /delete_solution_list/solution_list.xlsx
    ```
  - respond sample:
    ```json
    { "Message": "solution_list.xlsx deleted successfully" }
    ```

---

### 3.7 Accept request form

- 路徑：[POST] /data/accept
- 描述：Admin 進行 accept 動作
- request:
  - Content-Type: application/json
  - request parameter:

  | 參數     | 型別 | 必填 | 說明             | 範例                   |
  |----------|------|------|------------------|------------------------|
  | form_id  | str  | Y    | request form id  | 20250630_1751271939265 |
  | name     | str  | Y    | 員工英文名字     | Peter YH Chang         |
  | eid      | str  | Y    | 員工工號         | 11010059               |
  | due_date | str  | Y    | 模擬到期日       | 2024-07-10             |

- respond: `application/json`
- error message:
    ```json
    { "Error": "Permission Denied to Accept!" }
    { "Error": "No Request Form: form_id='xxx'" }
    { "Error": "form_id='xxx' Accepted Failed!" }
    { "detail": "INTERNAL_ERROR" }
    ```
- sample:
  - request sample:
    ```json
    {
      "form_id": "20250630_1751271939265",
      "name": "Peter YH Chang",
      "eid": "11010059",
      "due_date": "2024-07-10"
    }
    ```
  - respond sample:
    ```json
    { "Message": "form_id='20250630_1751271939265' Accepted." }
    ```
    - error message:
    ```json
    { "Error": "No Request Form: form_id='xxx'" }
    ```
---

### 3.8 Reject request form

- 路徑：[POST] /data/reject
- 描述：Admin 進行 reject 動作
- request:
  - Content-Type: application/json
  - request parameter:

  | 參數     | 型別 | 必填 | 說明             | 範例                   |
  |----------|------|------|------------------|------------------------|
  | form_id  | str  | Y    | request form id  | 20250630_1751271939265 |
  | name     | str  | Y    | 員工英文名字     | Peter YH Chang         |
  | eid      | str  | Y    | 員工工號         | 11010059               |
  | reason   | str  | Y    | 拒絕原因         | 內容不符需求           |

- respond: `application/json`
- error message:
    ```json
    { "Error": "Permission Denied to Reject!" }
    { "Error": "No Request Form: form_id='xxx'" }
    { "Error": "form_id='xxx' Rejected Failed!" }
    { "detail": "INTERNAL_ERROR" }` (500)
    ```
- sample:
  - request sample:
    ```json
    {
      "form_id": "20250630_1751271939265",
      "name": "Peter YH Chang",
      "eid": "11010059",
      "reason": "內容不符需求"
    }
    ```
  - respond sample:
    ```json
    { "Message": "form_id='20250630_1751271939265' Rejected." }
    ```
  - error message:
    ```json
    { "Error": "No Request Form: form_id='xxx'" }
    ```
---

### 3.9 完成模擬結果

- 路徑：[POST] /data/finished_request
- 描述：由 Admin 上傳模擬結果，Finish 此 request form
- request:
  - Content-Type: application/json
  - request parameter:

  | 參數              | 型別  | 必填 | 說明                  | 範例                   |
  |-------------------|-------|------|-----------------------|------------------------|
  | form_id           | str   | Y    | request form id       | 20250630_1751271939265 |
  | name              | str   | Y    | 員工英文名字          | Peter YH Chang         |
  | eid               | str   | Y    | 員工工號              | 11010059               |
  | kpi               | dict  | Y    | KPI 指標資料          | {"me_solution_compare":[6,6],...} |
  | solution_pdf_name | str   | Y    | solution list(pdf)    | solution.pdf           |
  | result_pdf_name   | str   | Y    | result pdf            | result.pdf             |
  | image_list        | list  | Y    | result png 檔案名(可多個) | ["img1.png","img2.png"]|

- respond: `application/json`
- error message:
    ```json
    { "Error": "Permission Denied to Finish Request!" }
    { "Error": "form_id Cannot Be Empty!" }
    { "Error": "kpi Cannot Be Empty!" }
    { "Error": "Solution List Cannot Be Empty!" }
    { "Error": "Simulation Result Cannot Be Empty!" }
    { "Error": "Me images Cannot Be Empty!" }
    { "Error": "No Request Form: form_id='xxx'" }
    { "Error": "Permission Denied Data" }
    { "Error": "form_id='xxx' Finished Failed!" }
    { "Error": "form_id='xxx' Had Finished Simulation, Do Not Update This Request." }
    { "detail": "INTERNAL_ERROR" }
    ```
- sample:
  - request sample:
    ```json
    {
      "form_id": "20250630_1751271939265",
      "name": "Peter YH Chang",
      "eid": "11010059",
      "kpi": {
        "me_solution_compare": [6, 6],
        "cost_compare": [0.5555, 0.4444],
        "num_me_position_compare": [5, 4],
        "me_index_compare": [0.6, 0.4]
      },
      "solution_pdf_name": "solution.pdf",
      "result_pdf_name": "result.pdf",
      "image_list": ["img1.png", "img2.png"]
    }
    ```
  - respond sample:
    ```json
    { "Message": "form_id='20250630_1751271939265' Finished." }
    ```
  - error message:
    ```json
    { "Error": "No Request Form: form_id='xxx'" }
    ```

---

### 3.10 上傳模擬 PDF

- 路徑：[POST] /data/upload_pdf_result
- 描述：上傳 solution_list 或 simulation result PDF
- request:
  - Content-Type: multipart/form-data
  - request body:
    | 參數     | 型別      | 說明      |
    |----------|-----------|-----------|
    | form_id  | str       | request form id |
    | file     | str       | solution_list 或 result |
    | pdf      | UploadFile| 上傳的 PDF 檔案 |
- respond: `application/json`
- error message: 詳見下方
- sample:
  - request sample: 
    ```
    form-data:
      form_id: 20250630_1751271939265
      file: solution_list
      pdf: solution.pdf
    ```
  - respond sample:
    ```json
    { "form_id": "20250630_1751271939265", "download_url": "/download_pdf/20250630_1751271939265/solution_list/solution.pdf" }
    ```
  - error message:
    ```json
    { "detail": "INTERNAL_ERROR"}
    ```

---

### 3.11 下載/預覽 PDF

- 路徑：[GET] /download_pdf/{form_id}/{file}/{filename}
- 描述：下載/預覽指定 PDF
- request:
  - Content-Type: 無
  - request parameter:

    | 參數     | 型別 | 必填 | 說明            | 範例                   |
    |----------|------|------|-----------------|------------------------|
    | form_id  | str  | Y    | request form id | 20250630_1751271939265 |
    | file     | str  | Y    | 類型            | solution_list          |
    | filename | str  | Y    | 檔案名稱        | solution.pdf           |

- respond: PDF 檔案下載 （PDF, 以 Content-Disposition: inline）
- error message:
    ```json
    { "Error": "PDF Cannot Be Found" }
    ```
- sample:
  - request sample:
    ```
    Get /download_pdf/20250630_1751271939265/solution_list/solution.pdf
    ```
---

### 3.12 刪除 PDF

- 路徑：[DELETE] /delete_pdf/{form_id}/{file}/{filename}
- 描述：刪除指定 PDF 檔案
- request:
  - Content-Type: 無
  - request parameter:

  | 參數     | 型別 | 必填 | 說明            | 範例                   |
  |----------|------|------|-----------------|------------------------|
  | form_id  | str  | Y    | request form id | 20250630_1751271939265 |
  | file     | str  | Y    | 類型            | solution_list          |
  | filename | str  | Y    | 檔案名稱        | solution.pdf           |

- respond: `application/json`
- error message:
    ```json
    { "Error": "PDF Cannot Be Found" }
    { "detail": "INTERNAL_ERROR" }
    ```
- sample:
  - request sample:
    ```
    DELETE /delete_pdf/20250630_1751271939265/solution_list/solution.pdf
    ```
  - respond sample:
    ```json
    { "Message": "solution.pdf deleted successfully" }
    ```
  - error message:
    ```json
    { "detail": "INTERNAL_ERROR"}
    ```
---

### 3.13 上傳模擬圖片

- 路徑：[POST] /data/upload_plot_result
- 描述：由 Admin 上傳模擬結果的圖片檔
- request:
  - Content-Type: multipart/form-data
  - request body:
    | 參數    | 型別      | 說明         |
    |---------|-----------|--------------|
    | form_id | str       | request form id |
    | images  | List[UploadFile] | 支援 jpg/png |
- respond: `application/json`
- error message:
    ```json
    { "Error": "Invalid image type: {filename}" }
    { "detail": "INTERNAL_ERROR" }
    ```
- sample:
  - request sample: 
    ```
    form-data:
      form_id: 20250630_1751271939265
      images: [png1,png2]
    ```
  - respond sample:
    ```json
    { "form_id": "20250630_1751271939265", "download_urls": ["/download_plot/20250630_1751271939265/img1.png"] }
    ```
  - error message:
    ```json
    { "detail": "INTERNAL_ERROR"}
    ```

---

### 3.14 下載/預覽模擬圖片

- 路徑：[GET] /download_plot/{form_id}/{filename}
- 描述：下載/預覽圖片
- request:
  - Content-Type: 無
  - request parameter:

  | 參數     | 型別 | 必填 | 說明            | 範例                   |
  |----------|------|------|-----------------|------------------------|
  | form_id  | str  | Y    | request form id | 20250630_1751271939265 |
  | filename | str  | Y    | 檔案名稱        | img1.png               |

- respond: 檔案下載
- error message:
    ```json
    { "Error": "Plot Cannot Be Found" }
    ```
- sample:
  - request sample:
    ```
    GET /download_plot/20250630_1751271939265/img1.png
    ```

---

### 3.15 刪除所有模擬圖片

- 路徑：[DELETE] /delete_plot/{form_id}
- 描述：刪除所有圖片
- request:
  - Content-Type: 無
  - request parameter:

  | 參數     | 型別 | 必填 | 說明            | 範例                   |
  |----------|------|------|-----------------|------------------------|
  | form_id  | str  | Y    | request form id | 20250630_1751271939265 |

- respond: `application/json`
- error message: 詳見下方
- sample:
  - request sample:
    ```
    DELETE /delete_plot/20250630_1751271939265
    ```
  - respond sample:
    ```json
    { "Message": "Deleted successfully" }
    ```
  - error message:
    ```json
    { "Error": "Plot Cannot Be Found" }
    ```
---

### 3.16 取得角色白名單

- 路徑：[GET] /data/get_role_list
- 描述：取得所有角色清單
- request:
  - Content-Type: 無
  - request parameter: 無
- respond: `application/json`
- error message: 詳見下方
- sample:
  - request sample:
    ```
    Get /data/get_role_list
    ```
  - respond sample:
    ```json
    { "role_list": [ ... ] }
    ```
  - error message:
    ```json
    { "Error": "Get Role Fail! ..."  }
    ```
---

### 3.17 查詢 eID 身分

- 路徑：[POST] /data/check_role
- 描述：查詢 eID 為 Admin 或 User
- request:
  - Content-Type: application/json
  - request parameter:

  | 參數 | 型別 | 必填 | 說明    | 範例     |
  |------|------|------|---------|----------|
  | eid  | str  | Y    | 員工工號 | 11010059 |
- respond: `application/json`
- error message: 詳見下方
- sample:
  - request sample:
    ```json
    { "eid": "11010059" }
    ```
  - respond sample:
    ```json
    { "Message": "Admin" }
    ```
  - error message:
    ```json
    { "Error": "Check Role Fail! ..."  }
    ```

---

### 3.18 新增/設定 eID 身分

- 路徑：[POST] /data/set_role
- 描述：新增/設定 eID 身分
- request:
  - Content-Type: application/json
  - request parameter:

  | 參數 | 型別 | 必填 | 說明        | 範例             |
  |------|------|------|-------------|------------------|
  | name | str  | Y    | 員工英文名字 | Peter YH Chang   |
  | eid  | str  | Y    | 員工工號     | 11010059         |
  | role | str  | Y    | 角色        | Admin            |
- respond: `application/json`
- error message: 詳見下方
- sample:
  - request sample:
    ```json
    { "name": "Peter YH Chang",
      "eid": "11010059",
      "role": "Admin"
     }
    ```
  - respond sample:
    ```json
    { "Message": "Set eID=11010059/ name=Peter YH Chang/ role=Admin" }
    ```
  - error message:
    ```json
    { "Error": "Set Role Fail! ..."  }
    ```

---

### 3.19 刪除 eID 身分

- 路徑：[DELETE] /data/delete_role
- 描述：刪除 eID 角色
- request:
  - Content-Type: application/json
  - request parameter:

  | 參數 | 型別 | 必填 | 說明    | 範例     |
  |------|------|------|---------|----------|
  | eid  | str  | Y    | 員工工號 | 11010059 |

- respond: `application/json`
- error message:
    ```json
    { "Error": "eID=xxx not found" }
    { "Error": "Delete role failed: ..." }
    ```
- sample:
  - request sample:
    ```json
    { 
        "eid": "11010059" 
     }
    ```
  - respond sample:
    ```json
    { "Message": "Set eID=11010059/ name=Peter YH Chang/ role=Admin" }
    ```
  - error message:
    ```json
    { "Error": "eID=xxx not found"  }
    ```

---

## 4. 通用錯誤格式

- CSRF token 驗證失敗
    ```json
    { "detail": "Invalid CSRF Token" }
    ```
- 其他錯誤
    ```json
    { "detail": "INTERNAL_ERROR" }
    ```

---