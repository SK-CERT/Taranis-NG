import axios from 'axios'

var abortControllers = {};

const ApiService = {

    init(baseURL) {
        axios.defaults.baseURL = baseURL;
        ApiService.setHeader();
    },

    setHeader() {
        if (localStorage.ACCESS_TOKEN) {
            axios.defaults.headers.common["Authorization"] = `Bearer ${localStorage.ACCESS_TOKEN}`
        } else {
            axios.defaults.headers.common = {}
        }
    },

    get(resource, data = {}) {
        // console.debug("GET:", resource);
        return axios.get(resource, data)
    },

    getWithCancel(resType, resource) {
        // resType: cancel key that abort request (support for multiple cancels)
        if (resType in abortControllers) {
            // console.debug("CANCEL", resType);
            abortControllers[resType].abort();
        }

        abortControllers[resType] = new AbortController();
        let promise = axios.get(resource, {
            signal: abortControllers[resType].signal
        }).catch(function (e) {
            if (axios.isCancel(e)) {
                // eslint-disable-next-line no-console
                console.debug("Request canceled:", resource);
            } else {
                throw e;
            }
        });
        // console.debug("GET CANCEL:", resource, promise);
        return promise;
    },

    post(resource, data) {
        return axios.post(resource, data)
    },

    put(resource, data) {
        return axios.put(resource, data)
    },

    delete(resource) {
        return axios.delete(resource)
    },

    upload(resource, form_data) {
        return axios.post(resource, form_data, {
            headers: {
                "Content-Type": "multipart/form-data"
            }
        });
    },

    async download(resource, data = {}, fileName = "download") {
        try {
            // Make the Axios request
            const config = {
                url: resource,          // full API path
                method: "POST",         // matches backend post()
                responseType: "blob",   // get raw data
                data: data,
            };

            const response = await axios(config);

            // Determine filename from header
            let filename = fileName;
            const disposition = response.headers["content-disposition"];
            if (disposition) {
                // handles: attachment; filename = report.pdf  filename = "report.pdf"  filename*=UTF-8''my%20report.pdf
                const match = disposition.match(/filename\*?=(?:UTF-8'')?["]?([^";\r\n]+)["]?/i);
                if (match) filename = match[1];
            }

            // Wrap in Blob for download
            const blob = new Blob([response.data]);
            const url = window.URL.createObjectURL(blob);

            const link = document.createElement("a");
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();

            window.URL.revokeObjectURL(url);
        } catch (err) {
            // eslint-disable-next-line no-console
            console.error("Download failed:", err);
        }
    },
};

export default ApiService
