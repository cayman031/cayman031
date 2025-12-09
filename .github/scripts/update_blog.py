import feedparser
import re
from datetime import datetime

def clean_html(raw_html):
    """HTML 태그 제거하고 텍스트만 추출하는 함수"""
    # HTML 태그 제거를 위한 정규표현식
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)

    # 줄바꿈과 연속된 공백을 하나의 공백으로 치환 (테이블 깨짐 방지)
    cleantext = re.sub(r'\\\\s+', ' ', cleantext)
    return cleantext.strip()

def get_thumbnail(entry):
    """RSS 엔트리에서 썸네일 이미지 URL을 추출하는 함수"""

    # 우선순위 1: RSS의 media:thumbnail 태그 확인
    if hasattr(entry, 'media_thumbnail'):
        return entry.media_thumbnail[0]['url']

    # 우선순위 2: enclosure 태그에서 이미지 타입 확인
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enclosure in entry.enclosures:
            if enclosure.get('type', '').startswith('image/'):
                return enclosure.get('url')

    # 우선순위 3: 본문(description)에서 첫 번째 이미지 추출
    if hasattr(entry, 'description'):
        img_match = re.search(r'<img[^>]+src="([^"]+)"', entry.description)
        if img_match:
            return img_match.group(1)

    # 모두 없을 경우 기본 이미지 반환
    return "<https://github.com/user-attachments/assets/9ffcad01-a362-4ad3-b3eb-f648be5d75de>"

def format_date(date_str):
    """RSS의 날짜를 YYYY.MM.DD 형식으로 변환하는 함수"""
    try:
        # RSS 표준 날짜 형식 파싱
        date_obj = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        return date_obj.strftime('%Y.%m.%d')
    except:
        # 파싱 실패 시 원본 그대로 반환
        return date_str

def create_blog_table(feed_url, max_posts=6):
    """RSS 피드에서 블로그 글을 가져와 3x2 테이블 형태의 마크다운 생성"""

    # RSS 피드 파싱
    feed = feedparser.parse(feed_url)
    entries = feed.entries[:max_posts]  # 최신 글만 가져오기

    # 마크다운 테이블 헤더 생성 (왼쪽 정렬)
    table = "| | | |\\\\n"
    table += "|---|---|---|\\\\n"

    # 3개씩 묶어서 행 생성 (2행 구성)
    for i in range(0, len(entries), 3):
        row_entries = entries[i:i+3]
        row = "|"

        for entry in row_entries:
            # 각 글의 정보 추출
            thumbnail = get_thumbnail(entry)  # 썸네일 이미지
            title = entry.title  # 글 제목
            link = entry.link  # 글 링크
            description = clean_html(entry.get('description', ''))[:50] + '...'  # 내용 미리보기 (50자 제한)
            pub_date = format_date(entry.get('published', ''))  # 발행일

            # 셀 내용 구성: 이미지(300x200 고정), 제목, 설명, 날짜
            cell = f'
**[{title}]({link})**
{description}
{pub_date}'
            row += f" {cell} |"

        # 3개 미만인 경우 빈 셀로 채우기
        while len(row_entries) < 3:
            row += " |"
            row_entries.append(None)

        table += row + "\\\\n"

    return table

def update_readme(readme_path, table_content):
    """README.md 파일의 마커 사이 내용을 새로운 테이블로 업데이트"""

    # README.md 읽기
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 업데이트할 영역을 나타내는 마커
    start_marker = ""
    end_marker = ""

    # 마커 위치 찾기
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    # 마커가 있으면 내용 교체
    if start_idx != -1 and end_idx != -1:
        new_content = (
            content[:start_idx + len(start_marker)] +
            "\\\\n" + table_content + "\\\\n" +
            content[end_idx:]
        )

        # README.md 파일에 쓰기
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print("✅ README.md updated successfully!")
    else:
        print("❌ Could not find markers in README.md")

if __name__ == "__main__":
    # ⚠️ 본인의 Tistory 블로그 URL로 변경하세요!
    RSS_FEED_URL = "<https://cayman031.tistory.com/rss>"
    README_PATH = "README.md"

    print("📡 Fetching blog posts from RSS feed...")
    table = create_blog_table(RSS_FEED_URL, max_posts=6)

    print("📝 Updating README.md...")
    update_readme(README_PATH, table)

</img[^>