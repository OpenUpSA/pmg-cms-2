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
var $readMore = $('.read-more a');
var showingSearchResult = false;

// Committee list page methods and handlers
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

// Committee detail page methods and handlers
var filterMeetings = function($target) {
  var filter = $target.attr('data-filter');
  var $table = $('#m-' + filter);

  $cdListTables.hide();
  $table.fadeIn({ duration: 250, easing: 'linear' });

  return filter;
}

$cdNavItem.on('click', function(e) {
  e.preventDefault();
  $(this).tab('show');

  $cdNavMobileSelect.val($(e.target).attr('data-target'));
});

$cdNavMobileSelect.on('change', function(e) {
  e.preventDefault();

  var $selected = $('option:selected',this);
  $selected.tab('show');
  $cdNavItem.closest('li')
    .removeClass('active')
    .has('[data-target="' + $selected.attr('data-target') + '"]')
    .addClass('active');
});

$cdFilterBtns.on('click', function(e) {
  var $target = $(e.target);
  var filter = filterMeetings($target);

  $cdFilterBtns.removeClass('active');
  $target.addClass('active');

  $cdFilterMobileSelect.val(filter);
});

$cdFilterMobileSelect.on('change', function(e) {
  var filter = filterMeetings($('option:selected',this));

  $cdFilterBtns.removeClass('active')
    .filter('[data-filter="' + filter + '"]')
    .addClass('active');
});

// Need to activate the first available filter
$cdFilterBtns.first()
  .trigger('click');

// Google analytics for summary read more
$readMore.on('click', function() {
  if(ga) ga('send','event','committee','summary-read-more');
});
