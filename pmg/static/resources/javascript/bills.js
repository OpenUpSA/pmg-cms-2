$(function() {
  // show bill version pdfs
  $('.bill-version-content a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
    var url = e.target.getAttribute('data-url'),
        pane = document.getElementById(e.target.getAttribute('href').slice(1));

    showBillPdf(pane, url);
  });

  // show the first tab when the page loads
  var firstTab = $('.bill-version-content a[data-toggle="tab"]')[0],
      pane = document.getElementById(firstTab.getAttribute('href').slice(1)),
      url = firstTab.getAttribute('data-url');

  showBillPdf(pane, url);

  function showBillPdf(pane, url) {
    var wrapper = $(pane).find('.bill-version-wrapper')[0];
    if (wrapper.children.length > 0) return;

    // Loaded via <script> tag, create shortcut to access PDF.js exports.
    var PDFJS = window['pdfjs-dist/build/pdf'];

    // The workerSrc property shall be specified.
    PDFJS.GlobalWorkerOptions.workerSrc = '//mozilla.github.io/pdf.js/build/pdf.worker.js';

    // Asynchronous download of PDF
    PDFJS.getDocument(url).then(function(pdf) {
      function renderPage(page) {
        renderPdfPage(pdf, page, wrapper);
      }

      for (var i = 1; i <= pdf.numPages; i++) {
        pdf.getPage(i).then(renderPage);
      }

    }, function (reason) {
      // PDF loading error
      console.error(reason);
    });
  }

  function renderPdfPage(pdf, pdfPage, wrapper) {
    var scale, viewport, canvas;

    if (wrapper.clientWidth > 800) {
      scale = 1.2;
    } else {
      scale = (wrapper.clientWidth - 40) / pdfPage.getViewport(1).width;
    }

    viewport = pdfPage.getViewport(scale);
    canvas = document.createElement('canvas');

    wrapper.appendChild(canvas);

    // Prepare canvas using PDF page dimensions
    var context = canvas.getContext('2d');
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    // Render PDF page into canvas context
    pdfPage.render({
      canvasContext: context,
      viewport: viewport
    });
  }
});
