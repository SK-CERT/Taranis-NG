var manifestUrl = "";
var language = navigator.language || "en";

if (language == "cs-CZ" || language == "cs"){
  manifestUrl = "/manifest-cs.json"
};

if (language == "sk-SK" || language == "sk"){
  manifestUrl = "/manifest-sk.json"
};

if (!manifestUrl) manifestUrl = "/manifest-en.json";

document.querySelector('#manifest-placeholder').setAttribute('href', manifestUrl);
