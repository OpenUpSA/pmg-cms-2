var $search = $('#committee-search');
var $searchInput = $('#committee-search input');
var $searchResult = $('.committee-search-result');
var $resultsFound = $('.results-found');
var $noResults = $('.no-results');
var $clearResults = $('.clear-results');
var $committees = $('.committees-list .nat .committee');
var $committeesList = $('.committees-list');
var $committeeNavItem = $('.committee-nav a, .committee-dd-nav a');
var showingSearchResult = false;

function clearSearchResult() {
  $searchResult.find('.left ul, .right ul')
    .empty();
  $noResults.hide();
  $resultsFound.hide();
  $searchInput.val('');
  $committeesList.show();
}

$committeeNavItem.on('click', function (e) {
  e.preventDefault();
  $(this).tab('show');
  $committees = $('.committees-list .tab-pane.active .committee');

  if(showingSearchResult) clearSearchResult();
});

$clearResults
  .on('click', function() {
    clearSearchResult();
    $clearResults.hide();
  });

$searchInput.on('focus', function() {
  $(document).on('keypress', function(e) {
    var value = $searchInput.val();
    if(e.which === 13) {
      var $results = [];
      var resultsCount = 0;

      showingSearchResult = true;

      clearSearchResult();
      $committeesList.hide();
      $clearResults.show();

      $committees.each(function() {
        var $self = $(this);

        if($self.find('a').text().toLowerCase().includes(value.toLowerCase())) {
          $results.push($self.clone());
        }
      });

      resultsCount = $results.length;

      if(!!resultsCount) {
        $resultsFound.show();

        if(resultsCount >= 40) {
          $searchResult.find('.left ul')
            .append($results.slice(0,resultsCount / 2 - 1));
          $searchResult.find('.right ul')
            .append($results.slice(resultsCount,resultsCount - 1))
        } else {
          $searchResult.find('.left ul')
            .append($results);
        }
      } else {
        $noResults.show();
      }
    }
  });
});

$searchInput.on('blur', function() {
  $(document).off('keypress');
})
