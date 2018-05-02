$(function() {
  function showBillPdf(version_id) {
    var pane = document.getElementById(version_id),
        url = pane.getAttribute('data-url'),
        wrapper = pane.querySelector('.bill-version-wrapper');

    if (wrapper.getAttribute('data-loaded')) return;

    $(wrapper).empty();

    // Asynchronous download of PDF
    PDFJS.getDocument(url).then(function(pdf) {
      wrapper.setAttribute('data-loaded', true);

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

  function autoShowBillPdf(version_id) {
    // assume small clients want to opt-in to showing the pdf
    if (window.outerWidth > 800) showBillPdf(version_id);
  }

  // show when button clicked
  $('.bill-version-content .load-pdf').on('click', function(e) {
    showBillPdf($(e.target).closest('.tab-pane').attr('id'));
  });

  // show bill version pdfs when tab changes
  $('.bill-version-content a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
    var id = e.target.getAttribute('href').slice(1);
    autoShowBillPdf(id);
  });

  // show the first tab when the page loads
  var firstTab = $('.bill-version-content a[data-toggle="tab"]')[0];
  autoShowBillPdf(firstTab.getAttribute('href').slice(1));
});
