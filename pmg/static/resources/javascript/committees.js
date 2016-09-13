var currentDate = new Date();
// Committee list DOM
var $search = $('#committee-search');
var $searchInput = $('#committee-search input');
var $searchResult = $('.committee-search-result');
var $resultsFound = $('.results-found');
var $noResults = $('.no-results');
var $clearResults = $('.clear-results');
var $committees = $('.committees-list .nat .committee');
var $committeesList = $('.committees-list');
var $committeeNavItem = $('.committee-nav a, .committee-dd-nav a');
// Committee details DOM
var $cdNavItem = $('.cte-meetings-nav a');
var $cdNavMobileSelect = $('.cte-meetings-nav-mobile select');
var $cdFilterBtns = $('.cte-meetings-filter-inner button');
var $cdFilterMobileSelect = $('.cte-meetings-filter-mobile select');
var $cdListTables = $('.cte-meetings-list .table');
var $cdCurrentYearTable = $('#m-' + currentDate.getFullYear());
var showingSearchResult = false;

var clearSearchResult = function() {
  $searchResult.find('.left ul, .right ul')
    .empty();
  $noResults.hide();
  $resultsFound.hide();
  $committeesList.show();
}

// Underscore debounce
var debounce = function(func, wait, immediate) {
	var timeout;
	return function() {
		var context = this, args = arguments;
		var later = function() {
			timeout = null;
			if (!immediate) func.apply(context, args);
		};
		var callNow = immediate && !timeout;
		clearTimeout(timeout);
		timeout = setTimeout(later, wait);
		if (callNow) func.apply(context, args);
	};
};

var typeAhead = debounce(function() {
  var value = $searchInput.val();

  clearSearchResult();

  if(!!value.length) {
    var $results = [];
    var resultsCount = 0;

    showingSearchResult = true;

    $committeesList.hide();
    $noResults.hide();
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
      $resultsFound.hide();
      $noResults.show();
    }
  }
},200);

$committeeNavItem.on('click', function(e) {
  e.preventDefault();
  $(this).tab('show');
  $committees = $('.committees-list .tab-pane.active .committee');

  if(showingSearchResult) clearSearchResult();
});

$searchInput.on('keyup', typeAhead);

// Committee detail page
var filterMeetings = function($target) {
  var filter = $target.attr('data-filter');
  var year = $target.attr('data-year');
  var $table = $('#m-' + year);
  var $rows = $table.find('tr');

  $cdFilterBtns.removeClass('active');
  $target.addClass('active');
  $cdListTables.hide();
  $cdListTables.find('tr')
    .show();

  switch(filter) {
    case 'recent':
      $rows.slice(10)
        .hide();
      break;
    case 'six-months':
      $rows.each(function(i,row) {
        var $row = $(row);
        var date = new Date($row.attr('data-date'));

        if(currentDate.getMonth() - date.getMonth() > 6) $row.hide();
      });
      break;
  }

  $table.fadeIn({ duration: 250, easing: 'linear' });
}

$cdNavItem.on('click', function(e) {
  e.preventDefault();
  $(this).tab('show');
});

$cdNavMobileSelect.on('change', function(e) {
  e.preventDefault();
  $('option:selected',this).tab('show');
});

// Hide all but first ten meetings on load
$cdCurrentYearTable.find('tr')
  .slice(10)
  .hide();

$cdFilterBtns.on('click', function(e) {
  filterMeetings($(e.target));
});

$cdFilterMobileSelect.on('change', function(e) {
  filterMeetings($('option:selected',this));
});
