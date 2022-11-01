function callApi(url, requestMethod) {
    var response = await fetch(url, {
        method: requestMethod,
        credentials: 'include'
    });

    var result;
    if (response.ok) {
        var contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('json')) {
            result = response.json();
        } else {
            result = response.text();
        }
    }

    return result;
}

var url = 'https://sellercentral.amazon.com/reportcentral/api/v1/getDownloadHistoryRecords?reportId=2500&isCountrySpecific=false';
var requestMethod = 'GET';

return callApi(url, requestMethod);