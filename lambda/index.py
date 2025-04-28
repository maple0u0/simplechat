# lambda/index.py
import json
import os
import re  # 正規表現モジュールをインポート
import urllib.request
import urllib.error


# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

INFERENCE_ENDPOINT = "https://b102-34-87-136-176.ngrok-free.app/generate"


def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        print("Using model:", "google/gemma-2-2b-jpn-it")
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            prompt += f"{role}: {content}\n"

        # ローカルAPIのリクエスト形式
        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        print("Calling local model API with payload:", json.dumps(request_payload))

        headers = {
            "Content-Type": "application/json"
        }

        # リクエストの準備
        req_data = json.dumps(request_payload).encode('utf-8')
        req = urllib.request.Request(
            INFERENCE_ENDPOINT,
            data=req_data,
            headers=headers,
            method='POST'
        )
        
        try:
            # APIの呼び出し
            with urllib.request.urlopen(req) as response:
                response_data = response.read()
                response_body = json.loads(response_data.decode('utf-8'))
                
                # レスポンスから応答テキストを取得
                assistant_response = response_body.get("generated_text", "")
                
                if not assistant_response:
                    raise Exception("APIからの応答が不正です")
                
        except urllib.error.URLError as e:
            raise Exception(f"API通信エラー: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("APIからの応答をJSONとしてパースできません")
        
        # 応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
