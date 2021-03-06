import os
import urllib
import base64
import time
import sys
import hmac
import hashlib
import alp
from alp.item import Item as I


def encodeRequestList(requestList, responseGroup, keywords=None):
    accessKeyID = "CHANGEME"

    defaultRequest = [
        "Service=AWSECommerceService",
        "AWSAccessKeyId=%s" % accessKeyID,
        "AssociateTag=CHANGEME"
    ]

    timeStamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    timeStampEnc = time.strftime("%Y-%m-%dT%H%%3A%M%%3A%SZ", time.gmtime())
    defaultRequest.append("Timestamp=%s" % timeStampEnc)
    responseGroupEnc = urllib.urlencode({"ResponseGroup": responseGroup})
    defaultRequest.append(responseGroupEnc)

    if keywords:
        keywordsEnc = urllib.quote(keywords)
        defaultRequest.append("Keywords=%s" % keywordsEnc)

    for item in defaultRequest:
        requestList.append(item)

    requestList.sort()
    requestToEncode = '&'.join(requestList)
    requestToEncode = "GET\nwebservices.amazon.com\n/onca/xml\n" + requestToEncode

    hm = hmac.new("CHANGEME", requestToEncode, hashlib.sha256)
    signature = base64.encodestring(hm.digest()).strip()
    requestList.append("Signature=%s" % signature)

    requestList.remove("Timestamp=%s" % timeStampEnc)
    requestList.append("Timestamp=%s" % timeStamp)
    requestList.remove(responseGroupEnc)
    requestList.append("ResponseGroup=%s" % responseGroup)

    if keywords:
        requestList.remove("Keywords=%s" % keywordsEnc)

    requestDict = {}
    for item in requestList:
        (k, _, v) = item.partition("=")
        requestDict[k] = v
    if keywords:
        requestDict["Keywords"] = keywords

    return requestDict


def cacheIcon(url):
    iconRequest = alp.Request(url)

    covercache = alp.cache("covercache")
    if not os.path.exists(covercache):
        os.makedirs(covercache)

    (_, filename) = os.path.split(url)
    iconPath = os.path.join(covercache, filename)
    with open(iconPath, "wb") as f:
        f.write(iconRequest.request.content)

    return iconPath


def getData(asin):
    requestList = [
        "Operation=ItemLookup",
        "ItemId=%s" % asin,
    ]
    requestDict = encodeRequestList(requestList, "Medium")
    itemRequest = alp.Request("http://webservices.amazon.com/onca/xml", requestDict)
    soup = itemRequest.souper()
    try:
        imageURL = soup.find("smallimage").url.string
        imagePath = cacheIcon(imageURL)
    except Exception:
        imagePath = "icon.png"
    try:
        link = soup.find("detailpageurl").string
    except Exception:
        link = "http://www.amazon.com/dp/%s" % asin
    try:
        title = soup.find("title").string
    except Exception:
        title = "Title Missing"
    try:
        author = soup.find("author").string
    except Exception:
        author = "Author Missing"
    try:
        price = soup.find("listprice").formattedprice.string
    except Exception:
        price = "Price Missing"

    returnDict = {
        "uid": asin,
        "arg": link,
        "title": title,
        "subtitle": u"%s\u2014%s" % (author, price),
        "icon": imagePath
    }

    return returnDict


def doSearch():
    q = sys.argv[1:]
    q = ' '.join(q)

    requestList = [
        "Operation=ItemSearch",
        "SearchIndex=KindleStore",
        "Sort=relevancerank"
    ]
    # requestList.append(urllib.urlencode({"Keywords": q}))
    # kw = q.replace(" ", ",")
    # requestList.append("Keywords=%s" % kw)

    requestDict = encodeRequestList(requestList, "ItemIds", keywords=q)

    searchRequest = alp.Request("http://webservices.amazon.com/onca/xml", requestDict)
    soup = searchRequest.souper()

    resultsFeedback = []
    if soup.find("error"):
        e = soup.error.message.string
        resultsFeedback.append(I(title="Bad Request", subtitle=e, valid=False))

    else:
        asins = soup.find_all("asin")

        for asin in asins:
            aResult = getData(asin.string)
            resultsFeedback.append(I(**aResult))

    if len(resultsFeedback) == 0:
        alp.feedback(I(title="No Results", subtitle="Your query returned 0 results.",
                        valid=False))
    else:
        alp.feedback(resultsFeedback)


if __name__ == "__main__":
    doSearch()
