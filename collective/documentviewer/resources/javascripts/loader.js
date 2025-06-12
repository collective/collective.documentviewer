
var launchDV = function () {
    documentviewer = document.querySelector('.pat-documentviewer');
    if (documentviewer) {
        options = JSON.parse(documentviewer.getAttribute('data-pat-documentviewer'));
        options.container = documentviewer;
        DV.load(options.data, options);
    }
}

document.addEventListener('DOMContentLoaded', launchDV);
