from bs4 import BeautifulSoup


def parse_comments(html, post_id):

    soup = BeautifulSoup(html, "html.parser")

    all_comments = []

    threads = soup.find_all("div", class_="thread")

    if not threads:
        print("No comment threads found.")

        return []

    for thread in threads:

        top_comment = thread.find("div", class_="comment")

        if top_comment:
            process_comment(
                top_comment,
                post_id=post_id,
                comments=all_comments,
                parent_comment_id=None,
                depth=0
            )

    return all_comments


def process_comment(
    comment,
    post_id,
    comments,
    parent_comment_id,
    depth
):

    comment_id = comment.get("id")

    # ---------- SCORE ----------
    score_tag = comment.find("p", class_="comment_score")
    score = None

    if score_tag:
        score_text = score_tag.get_text(strip=True)

        try:
            score = int(score_text)
        except ValueError:
            score = None

    # ---------- AUTHOR ----------
    author_tag = comment.find("a", class_="comment_author")
    author = author_tag.get_text(strip=True) if author_tag else None

    # ---------- CREATED ----------
    created_tag = comment.find("a", class_="created")
    created_at = created_tag.get("title") if created_tag else None

    # ---------- BODY ----------
    body_tag = comment.find("div", class_="comment_body")
    body = body_tag.get_text(" ", strip=True) if body_tag else ""

    comments.append({
        "comment_id": comment_id,
        "post_id": post_id,
        "parent_comment_id": parent_comment_id,
        "depth": depth,
        "author": author,
        "body": body,
        "score": score,
        "created_at": created_at
    })

    # ---------- REPLIES ----------
    replies = comment.find("div", class_="replies")

    if not replies:
        return

    child_comments = replies.find_all(
        "div",
        class_="comment",
        recursive=False
    )

    for child in child_comments:

        process_comment(
            child,
            post_id=post_id,
            comments=comments,
            parent_comment_id=comment_id,
            depth=depth + 1
        )

