var manifestUrl = "";
var language = navigator.language || "en";

if (language == "cs-CZ" || language == "cs"){
  manifestUrl = "/cs-manifest.json"
};

if (language == "sk-SK" || language == "sk"){
  manifestUrl = "/sk-manifest.json"
};

if (!manifestUrl) manifestUrl = "/en-manifest.json";

document.querySelector('#manifest-placeholder').setAttribute('href', manifestUrl);
