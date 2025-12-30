import os
import requests
from github import Github

def main():
    # 1. 환경변수 가져오기
    token = os.environ.get('NOTION_TOKEN')
    db_id = os.environ.get('NOTION_DATABASE_ID')
    gh_token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('GITHUB_REPOSITORY')

    # 2. 노션 헤더 설정
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # 3. 노션에서 Ready 상태인 것 찾기
    query_url = f"https://api.notion.com/v1/databases/{db_id}/query"
    payload = {
        "filter": {
            "property": "Status",
            "select": {"equals": "Ready"}
        }
    }
    
    res = requests.post(query_url, json=payload, headers=headers)
    data = res.json()
    
    pages = data.get("results", [])
    if not pages:
        print("No pages to sync.")
        return

    # 4. 깃허브 연결
    g = Github(gh_token)
    repo = g.get_repo(repo_name)

    # 5. 하나씩 이슈 생성 및 노션 업데이트
    for page in pages:
        try:
            # 제목 추출
            props = page['properties']
            # 제목이 비어있으면 건너뛰기
            if not props['이름']['title']: continue
            
            title = props['이름']['title'][0]['text']['content']
            page_id = page['id']
            page_url = page['url']
            
            # 이슈 생성
            body = f"Notion Link: {page_url}"
            repo.create_issue(title=title, body=body)
            print(f"Created issue: {title}")
            
            # 노션 상태 변경 (Synced)
            update_url = f"https://api.notion.com/v1/pages/{page_id}"
            update_data = {
                "properties": {
                    "Status": {"select": {"name": "Synced"}}
                }
            }
            requests.patch(update_url, json=update_data, headers=headers)
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
