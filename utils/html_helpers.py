from bs4 import BeautifulSoup


def filter_paragraphs_with_asterisk(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    filtered_paragraphs = []
    for p in soup.find_all("p"):
        a_tag = p.find("a")
        if a_tag and a_tag.text.startswith("*"):
            filtered_paragraphs.append(str(p))
    return filtered_paragraphs
