
var launchDV = function () {
    documentviewer = document.querySelector('.pat-documentviewer');
    if (documentviewer) {
        options = JSON.parse(documentviewer.getAttribute('data-pat-documentviewer'));
        console.log('IN LOADER with options:', options);
        options.container = documentviewer;
        DV.load(options.data, options);
    }
}

document.addEventListener('DOMContentLoaded', launchDV);
