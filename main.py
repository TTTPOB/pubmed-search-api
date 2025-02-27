import logging
import os
from dataclasses import dataclass
from typing import List
from urllib.parse import unquote

from Bio import Entrez
from fastapi import FastAPI
from pydantic import BaseModel

# set up logger to stderr
loglevel = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(
    level=loglevel, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
l = logging.getLogger(__name__)

# Set the Entrez email
Entrez.email = os.environ.get("ENTREZ_EMAIL", "not@set.com")


def submit_pubmed_query(query: str, retmax=10) -> List[str]:
    handle = Entrez.esearch(db="pubmed", term=query, retmax=retmax)
    record = Entrez.read(handle)
    l.debug(f"Found {record['Count']} articles")
    l.debug(f"IDs: {record['IdList']}")
    l.debug(f"Query translation: {record['QueryTranslation']}")
    handle.close()
    return record["IdList"]


def get_article_info(pmid: str | List[str]):
    if isinstance(pmid, list):
        pmid_str = ",".join(pmid)
    else:
        pmid_str = pmid

    # return doi, url, title, abstract, authors
    handle = Entrez.efetch(db="pubmed", id=pmid_str, retmode="xml")
    record = Entrez.read(handle)
    resp = []
    for a in record["PubmedArticle"]:
        doi = "DOI_NOT_PROVIDED"
        for id in a["PubmedData"]["ArticleIdList"]:
            if id.attributes["IdType"] == "doi":
                doi = id
                break
        url = f"https://doi.org/{doi}"
        title = a["MedlineCitation"]["Article"]["ArticleTitle"]
        abstract = a["MedlineCitation"]["Article"]["Abstract"]["AbstractText"]
        if isinstance(abstract, list):
            abstract = "\n".join(abstract)
        author_list = a["MedlineCitation"]["Article"]["AuthorList"]
        author_list = [
            f"{a.get("ForeName", "NAME")} {a.get("LastName", "NAME")}"
            for a in author_list
        ]
        resp.append(
            {
                "doi": doi,
                "url": url,
                "title": title,
                "abstract": abstract,
                "authors": author_list,
            }
        )
    handle.close()
    return resp


@dataclass
class ArticleInfo:
    doi: str
    url: str
    title: str
    abstract: str
    authors: List[str]


def re_encode(s: str) -> str:
    # remove url encode
    l.info(f"Re-encoding {s}")
    result = unquote(s)
    l.info(f"Unquoted: {result}")
    return result


app = FastAPI()


@app.get("/search")
def search(query: str, retmax: int = 10) -> List[str]:
    l.info(f"Searching for {query}")
    return submit_pubmed_query(re_encode(query), retmax)


@app.get("/article_info")
def article_info(pmid: str) -> List[ArticleInfo]:
    if "," in pmid:
        pmid = pmid.split(",")
    return get_article_info(pmid)


@app.get("/search_details")
def search_details(query: str, retmax: int = 10) -> List[ArticleInfo]:
    pmids = submit_pubmed_query(re_encode(query), retmax)
    return get_article_info(",".join(pmids))


if __name__ == "__main__":
    # get port from environment variable
    port = os.environ.get("PORT", 3003)
    listen = os.environ.get("LISTEN", "0.0.0.0")
    # run uvicorn server
    import uvicorn

    uvicorn.run(app, host=listen, port=port)
