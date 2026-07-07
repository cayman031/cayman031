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
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = text.replace("`", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_thumbnail(entry) -> str:
    """RSS 엔트리에서 썸네일 이미지 URL을 추출"""
    def _normalize_url(url: str) -> str:
        if not url: return url
        url = url.strip()
        if url.startswith("//"): url = "https:" + url
        elif url.startswith("http://"): url = url.replace("http://", "https://")
        return url

    if hasattr(entry, "media_thumbnail"):
        try:
            url = entry.media_thumbnail[0].get("url")
            if url: return _normalize_url(url)
        except Exception: pass

    if hasattr(entry, "enclosures") and entry.enclosures:
        for enclosure in entry.enclosures:
            if enclosure.get("type", "").startswith("image/"):
                url = enclosure.get("url")
                if url: return _normalize_url(url)

    if hasattr(entry, "description") and entry.description:
        img_match = re.search(r'<img[^>]+src="([^"]+)"', entry.description)
        if img_match: return _normalize_url(img_match.group(1))

    return "https://via.placeholder.com/300x200?text=No+Image"


def format_date(date_str: str) -> str:
    """RSS의 날짜를 YYYY.MM.DD 형식으로 변환"""
    if not date_str: return ""
    try:
        date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        return date_obj.strftime("%Y.%m.%d")
    except Exception: return date_str


def remove_title_from_description(title: str, description: str) -> str:
    """
    본문(description)이 제목(title)으로 시작하는 경우 중복을 제거합니다.
    대괄호 [], 특수문자, 공백 등을 무시하고 문자열의 순서만 비교합니다.
    예: Title="Gradle Build", Desc="[Gradle] Build 방법" -> Match! -> "방법" 반환
    """
    # 1. 비교를 위해 제목에서 알파벳/한글/숫자만 남김
    clean_title = re.sub(r"[^a-zA-Z0-9가-힣]", "", title).lower()
    
    if not clean_title:
        return description

    t_idx = 0
    d_idx = 0
    last_match_idx = -1
    
    # 2. 본문을 한 글자씩 순회하며 제목의 문자가 순서대로 나오는지 확인
    while d_idx < len(description) and t_idx < len(clean_title):
        d_char = description[d_idx]
        
        # 본문의 현재 글자가 문자/숫자라면 제목과 비교해야 함
        if d_char.isalnum():
            if d_char.lower() == clean_title[t_idx]:
                t_idx += 1
                last_match_idx = d_idx
            else:
                # 문자가 다른 경우 중복 아님 -> 원본 반환
                return description
        else:
            # 본문의 특수문자(괄호, 공백 등)는 건너뜀 (비교 안함)
            pass
            
        d_idx += 1

    # 3. 제목의 모든 문자가 본문 앞부분에서 순서대로 발견됨
    if t_idx == len(clean_title):
        # 마지막으로 일치한 지점 뒤부터 자름
        cut_desc = description[last_match_idx + 1:]
        # 앞부분에 남은 잔여 특수문자(-, :, ], 공백 등) 제거
        return cut_desc.lstrip(" -:|]")
    
    return description


def create_blog_table(feed_url: str, max_posts: int = 6) -> str:
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
            
            raw_desc = entry.get("description", "")
            description = clean_html(raw_desc)

            # --- [수정된 로직] 스마트한 중복 제거 ---
            description = remove_title_from_description(title, description)
            
            # 혹시 중복 제거가 안 되었더라도, 맨 앞의 단순 카테고리 태그 [Category]는 제거 시도
            # (제목과 본문이 완전히 달라서 위 함수가 실패했을 경우 대비)
            if description.startswith("[") and "]" in description[:20]:
                 description = re.sub(r"^\[[^\]]+\]\s*", "", description)
            # ------------------------------------

            # 길이 제한
            max_len = 100
            if len(description) > max_len:
                description = description[:max_len].rstrip() + "..."
            
            safe_title = re.sub(r"[\[\]\(\)`]", "", title)

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
    RSS_FEED_URL = "https://heygw44.tistory.com/rss"
    README_PATH = "README.md"

    print("📡 Fetching blog posts from RSS feed...")
    table = create_blog_table(RSS_FEED_URL, max_posts=6)

    print("📝 Updating README.md...")
    update_readme(README_PATH, table)
