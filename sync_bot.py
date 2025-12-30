import os
import requests
from github import Github

def get_page_content(page_id, headers):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    try:
        res = requests.get(url, headers=headers)
        blocks = res.json().get("results", [])
        
        content = ""
        for block in blocks:
            b_type = block['type']
            
            # 1. 하위 문서(Child Page) 처리
            if b_type == "child_page":
                child_title = block['child_page']['title']
                child_id = block['id']
                print(f"   -> 📂 하위 문서 진입: {child_title}")
                child_body = get_page_content(child_id, headers)
                content += f"\n---\n### 📂 {child_title}\n{child_body}\n---\n"
                continue

            # 2. 텍스트 내용 처리
            if 'rich_text' in block.get(b_type, {}):
                texts = block[b_type]['rich_text']
                if not texts: continue
                text_content = "".join([t['plain_text'] for t in texts])
                
                if b_type == "paragraph":
                    content += f"{text_content}\n\n"
                elif b_type.startswith("heading"):
                    content += f"## {text_content}\n\n"
                elif "list_item" in b_type:
                    content += f"- {text_content}\n"
                elif "to_do" in b_type:
                    state = "[x]" if block['to_do']['checked'] else "[ ]"
                    content += f"- {state} {text_content}\n"
                elif "code" in b_type:
                    content += f"```\n{text_content}\n```\n\n"
                elif "quote" in b_type:
                    content += f"> {text_content}\n\n"

        return content
    except Exception as e:
        print(f"Error: {e}")
        return ""

def main():
    token = os.environ.get('NOTION_TOKEN')
    db_id = os.environ.get('NOTION_DATABASE_ID')
    gh_token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('GITHUB_REPOSITORY')

    headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}

    # Ready 상태인 페이지 찾기
    query_url = f"https://api.notion.com/v1/databases/{db_id}/query"
    payload = {"filter": {"property": "Status", "select": {"equals": "Ready"}}}
    res = requests.post(query_url, json=payload, headers=headers)
    pages = res.json().get("results", [])

    if not pages:
        print("No pages to sync.")
        return

    g = Github(gh_token)
    repo = g.get_repo(repo_name)

    for page in pages:
        try:
            props = page['properties']
            if not props['이름']['title']: continue
            title = props['이름']['title'][0]['text']['content']
            page_id = page['id']
            page_url = page['url']
            
            # 내용 가져오기
            print(f"Processing: {title}")
            body_content = get_page_content(page_id, headers)
            
            # 이슈 생성 (내용 포함)
            issue_body = f"## 🔗 Notion Link\n{page_url}\n\n## 📝 내용\n{body_content}"
            repo.create_issue(title=title, body=issue_body)
            
            # 상태 변경
            update_url = f"https://api.notion.com/v1/pages/{page_id}"
            requests.patch(update_url, json={"properties": {"Status": {"select": {"name": "Synced"}}}}, headers=headers)
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
