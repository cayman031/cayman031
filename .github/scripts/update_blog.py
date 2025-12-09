import feedparser
import re
import html
from datetime import datetime


def clean_html(raw_html: str) -> str:
    """HTML/Markdown 태그 제거하고 텍스트만 추출하는 함수"""
    if not raw_html:
        return ""

    text = html.unescape(raw_html)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_thumbnail(entry) -> str:
    """RSS 엔트리에서 썸네일 이미지 URL을 추출하는 함수"""

    def _normalize_url(url: str) -> str:
        if not url:
            return url
        url = url.strip()
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("http://"):
            url = url.replace("http://", "https://")
        return url

    # 1. media_thumbnail
    if hasattr(entry, "media_thumbnail"):
        try:
            url = entry.media_thumbnail[0].get("url")
            url = _normalize_url(url)
            if url:
                return url
        except Exception:
            pass

    # 2. enclosures
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enclosure in entry.enclosures:
            if enclosure.get("type", "").startswith("image/"):
                url = _normalize_url(enclosure.get("url"))
                if url:
                    return url

    # 3. description 내 첫 번째 <img>
    if hasattr(entry, "description") and entry.description:
        img_match = re.search(r'<img[^>]+src="([^"]+)"', entry.description)
        if img_match:
            url = _normalize_url(img_match.group(1))
            if url:
                return url

    # 기본 이미지
    return "https://via.placeholder.com/300x200?text=No+Image"


def format_date(date_str: str) -> str:
    """RSS의 날짜를 YYYY.MM.DD 형식으로 변환"""
    if not date_str:
        return ""
    try:
        date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        return date_obj.strftime("%Y.%m.%d")
    except Exception:
        return date_str


def create_blog_table(feed_url: str, max_posts: int = 6) -> str:
    """RSS 피드에서 블로그 글을 가져와 3열 HTML 테이블 생성"""
    feed = feedparser.parse(feed_url)
    entries = feed.entries[:max_posts]

    if not entries:
        return "<p>최근 글이 없습니다.</p>"

    table = "<table>\n"

    for i in range(0, len(entries), 3):
        row_entries = entries[i: i + 3]
        while len(row_entries) < 3:
            row_entries.append(None)

        table += "  <tr>\n"

        for entry in row_entries:
            if entry is None:
                table += "    <td></td>\n"
                continue

            thumbnail = get_thumbnail(entry)
            title = clean_html(entry.title)
            link = entry.link
            pub_date = format_date(entry.get("published", ""))

            safe_title = re.sub(r"[\[\]\(\)`]", "", title)

            # description 제거 — 제목 + 이미지 + 날짜만 표시
            cell = (
                f'<a href="{link}">'
                f'<img src="{thumbnail}" alt="{safe_title}" width="300" height="200" />'
                f"</a><br/>"
                f'<strong><a href="{link}">{title}</a></strong><br/>'
                f"{pub_date}"
            )

            table += f"    <td>{cell}</td>\n"

        table += "  </tr>\n"

    table += "</table>\n"
    return table


def update_readme(readme_path: str, table_content: str) -> None:
    """README.md 파일의 마커 사이 내용을 새로운 테이블로 업데이트"""
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!-- BLOG-POST-LIST:START -->"
    end_marker = "<!-- BLOG-POST-LIST:END -->"

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx != -1 and end_idx != -1:
        new_content = (
            content[: start_idx + len(start_marker)]
            + "\n"
            + table_content
            + "\n"
            + content[end_idx:]
        )
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("✅ README.md updated successfully!")
    else:
        print("❌ Could not find markers in README.md")


if __name__ == "__main__":
    RSS_FEED_URL = "https://cayman031.tistory.com/rss"
    README_PATH = "README.md"

    print("📡 Fetching blog posts from RSS feed...")
    table = create_blog_table(RSS_FEED_URL, max_posts=6)

    print("📝 Updating README.md...")
    update_readme(README_PATH, table)
