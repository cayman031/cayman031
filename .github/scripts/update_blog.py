import feedparser
import re
from datetime import datetime


def clean_html(raw_html: str) -> str:
    """HTML/Markdown 태그 제거하고 텍스트만 추출하는 함수"""
    if not raw_html:
        return ""

    # 1) HTML 태그 제거
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)

    # 2) Markdown 링크 [text](url) -> text
    cleantext = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleantext)

    # 3) 굵게/기울임 표시 제거 **text** -> text, *text* -> text
    cleantext = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleantext)
    cleantext = re.sub(r"\*([^*]+)\*", r"\1", cleantext)

    # 4) 인라인 코드 백틱 제거 `code` -> code
    cleantext = cleantext.replace("`", "")

    # 5) 줄바꿈/여러 공백을 하나의 공백으로 치환
    cleantext = re.sub(r"\s+", " ", cleantext)

    return cleantext.strip()


def get_thumbnail(entry) -> str:
    """RSS 엔트리에서 썸네일 이미지 URL을 추출하는 함수"""

    def _normalize_url(url: str) -> str:
        """프로토콜/형식을 GitHub에서 안전하게 쓸 수 있도록 정리"""
        if not url:
            return url
        url = url.strip()
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("http://"):
            url = url.replace("http://", "https://")
        return url

    # 우선순위 1: media_thumbnail
    if hasattr(entry, "media_thumbnail"):
        try:
            url = entry.media_thumbnail[0].get("url")
            url = _normalize_url(url)
            if url:
                return url
        except Exception:
            pass

    # 우선순위 2: enclosures
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enclosure in entry.enclosures:
            if enclosure.get("type", "").startswith("image/"):
                url = _normalize_url(enclosure.get("url"))
                if url:
                    return url

    # 우선순위 3: description 내 첫 번째 <img>
    if hasattr(entry, "description") and entry.description:
        img_match = re.search(r'<img[^>]+src="([^"]+)"', entry.description)
        if img_match:
            url = _normalize_url(img_match.group(1))
            if url:
                return url

    # 모두 없을 경우 기본 이미지 (공용 placeholder)
    return "https://via.placeholder.com/300x200?text=No+Image"


def format_date(date_str: str) -> str:
    """RSS의 날짜를 YYYY.MM.DD 형식으로 변환하는 함수"""
    if not date_str:
        return ""

    try:
        # RSS 표준 날짜 형식 파싱
        date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        return date_obj.strftime("%Y.%m.%d")
    except Exception:
        # 파싱 실패 시 원본 그대로 반환
        return date_str


def create_blog_table(feed_url: str, max_posts: int = 6) -> str:
    """RSS 피드에서 블로그 글을 가져와 3열 HTML 테이블 생성"""

    # RSS 피드 파싱
    feed = feedparser.parse(feed_url)
    entries = feed.entries[:max_posts]  # 최신 글만 가져오기

    if not entries:
        return "<p>최근 글이 없습니다.</p>"

    # HTML 테이블 시작
    table = "<table>\n"

    # 3개씩 묶어서 행 생성
    for i in range(0, len(entries), 3):
        row_entries = entries[i: i + 3]

        # 3개 미만인 경우 None으로 채워서 3칸 맞추기
        while len(row_entries) < 3:
            row_entries.append(None)

        table += "  <tr>\n"

        for entry in row_entries:
            if entry is None:
                table += "    <td></td>\n"
                continue

            # 각 글의 정보 추출
            thumbnail = get_thumbnail(entry)                    # 썸네일 이미지
            title = entry.title                                 # 글 제목
            link = entry.link                                   # 글 링크
            description = clean_html(entry.get("description", ""))[:50] + "..."
            pub_date = format_date(entry.get("published", ""))  # 발행일

            # alt 텍스트에서 특수문자 제거
            safe_title = re.sub(r"[\[\]\(\)`]", "", title)

            # 셀 내용: HTML만 사용 (마크다운 X)
            cell = (
                f'<a href="{link}">'
                f'<img src="{thumbnail}" alt="{safe_title}" width="300" height="200" />'
                f"</a><br/>"
                f'<strong><a href="{link}">{title}</a></strong><br/>'
                f"{description}<br/>"
                f"{pub_date}"
            )

            table += f"    <td>{cell}</td>\n"

        table += "  </tr>\n"

    table += "</table>\n"
    return table


def update_readme(readme_path: str, table_content: str) -> None:
    """README.md 파일의 마커 사이 내용을 새로운 테이블로 업데이트"""

    # README.md 읽기
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 업데이트할 영역을 나타내는 마커
    # README.md 안에 반드시 아래 두 줄이 있어야 합니다.
    # <!-- BLOG-POST-LIST:START -->
    # <!-- BLOG-POST-LIST:END -->
    start_marker = "<!-- BLOG-POST-LIST:START -->"
    end_marker = "<!-- BLOG-POST-LIST:END -->"

    # 마커 위치 찾기
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    # 마커가 있으면 내용 교체
    if start_idx != -1 and end_idx != -1:
        new_content = (
            content[: start_idx + len(start_marker)]
            + "\n"
            + table_content
            + "\n"
            + content[end_idx:]
        )

        # README.md 파일에 쓰기
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print("✅ README.md updated successfully!")
    else:
        print("❌ Could not find markers in README.md")
        print("README.md 에 다음 두 마커가 존재하는지 확인하세요:")
        print(start_marker)
        print(end_marker)


if __name__ == "__main__":
    # 본인의 Tistory RSS URL
    RSS_FEED_URL = "https://cayman031.tistory.com/rss"
    README_PATH = "README.md"

    print("📡 Fetching blog posts from RSS feed...")
    table = create_blog_table(RSS_FEED_URL, max_posts=6)

    print("📝 Updating README.md...")
    update_readme(README_PATH, table)
