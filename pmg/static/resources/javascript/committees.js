var currentDate = new Date();
// Committee list DOM
var $cteList = $('.cte-list');
var $cteListItems = $('.cte-list .tab-pane.active .committee');
var $cteListSearchInput = $('.cte-list-search input');
var $cteListSearchResults = $('.cte-list-search-results');
var $cteListNavItem = $('.cte-list-nav a, .cte-list-mobile-nav option');
// Committee details DOM
var $cteDtlNavItem = $('.cte-dtl-meetings-nav a');
var $cteDtlNavMobileSelect = $('.cte-dtl-meetings-nav-mobile select');
var $cteDtlFilterSelect = $('.cte-dtl-meetings-filter select');
var $cteDtlListTables = $('.cte-dtl-meetings-list .table');
var $cteDtlReadMore = $('.read-more a');
var $cteDtlMtngsList = $('.cte-dtl-meetings-list');
var $cteDtlMtngsSearchInput = $('.cte-dtl-meetings-search input');
var $cteDtlMtngsSearchResults = $('.cte-dtl-meetings-search-results');
var showingSearchResult = false;
// General elements
var $cteTabNav = $('.cte-tab-nav');
var $cteTabNavItem = $('.cte-tab-nav a');
var $cteSelectTabNav = $('.cte-select-tab-nav');

// Committee list page methods and handlers
var clearSearchResult = function($list,$res,twoCol) {
  var $resultsList = $res.find('.results-list');

  $res.find('.no-results')
    .hide();

  if(twoCol) {
    $resultsList.find('.left, .right')
    .empty();
  } else {
    $resultsList.empty();
  }

  $resultsList.hide();
  $list.show();
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

var typeAhead = debounce(function($input,$list,$res,params) {
  var value = $input.val();
  var $noResults = $res.find('.no-results');
  var $resultsList = $res.find('.results-list');
  var $items = !!params && params.$items && params.$items.length ? params.$items : $list.find('.item');

  clearSearchResult($list,$res,!!params && params.twoCol ? params.twoCol : false);

  if(!!value.length) {
    var $results = [];
    var resultsCount = 0;

    showingSearchResult = true;

    $list.hide();
    $noResults.hide();

    $items.each(function() {
      var $self = $(this);

      if($self.find('a').text().toLowerCase().includes(value.toLowerCase())) {
        $results.push($self.clone());
      }
    });

    resultsCount = $results.length;

    if(!!resultsCount) {
      $resultsList.show();

      if(!!params && params.sort) {
        console.log('sorting');
        $results.sort(function(a,b) {
          console.log(a,b);
          return new Date(b.attr('data-date')) - new Date(a.attr('data-date'));
        });
        console.log($results);
      }

      if(!!params && params.twoCol) {
        var $resultsListLeft = $resultsList.find('.left');
        var $resultsListRight = $resultsList.find('.right');

        if(resultsCount > 20) {
          if(resultsCount < 40) {
            $resultsListLeft.append($results.slice(0,19));
            $resultsListRight.append($results.slice(20));
          } else {
            $resultsListLeft.append($results.slice(0,resultsCount / 2 - 1));
            $resultsListRight.append($results.slice(resultsCount / 2));
          }
        } else {
          $resultsListLeft.append($results);
        }
      } else {
        $resultsList
          .append($results);
      }
    } else {
      $resultsList.hide();
      $noResults.show();
    }
  }
},200);

var filterMeetings = function($target) {
  var filter = $target.attr('data-filter');
  var $table = $('#m-' + filter);

  $cteDtlListTables.hide();
  $table.fadeIn({ duration: 250, easing: 'linear' });

  return filter;
}

/**
 * Event handlers
 */

 // For pairing tab navs with selects
 $cteTabNavItem.on('click', function(e) {
   e.preventDefault();
   $(this).tab('show');

   $cteSelectTabNav.val($(e.target).attr('href'));
 });

 $cteSelectTabNav.on('change', function(e) {
   e.preventDefault();

   var $selected = $('option:selected',this);

   $selected.tab('show');
   $cteTabNav.find('li')
     .removeClass('active')
     .has('[href="' + $selected.attr('data-target') + '"]')
     .closest('li')
     .addClass('active');
 });

 // Committee list page
$cteListNavItem.on('click', function(e) {
  e.preventDefault();
  $cteListItems = $('.cte-list .tab-pane.active .committee');

  if(showingSearchResult) clearSearchResult($cteList,$cteListSearchResults,true);
});

$cteListSearchInput.on('keyup', function() {
  typeAhead($cteListSearchInput, $cteList, $cteListSearchResults, { $items: $cteListItems, twoCol: true })
});

// Committee detail page handlers
$cteDtlFilterSelect.on('change', function(e) {
  filterMeetings($('option:selected',this));
  $cteDtlMtngsSearchInput.val('');

  clearSearchResult($cteDtlMtngsList,$cteDtlMtngsSearchResults);
  $cteDtlMtngsList.show();
});

$cteDtlFilterSelect.on('focus', function() {
  this.selectedIndex = -1;
});

// Google analytics for summary read more
$cteDtlReadMore.on('click', function() {
  if(ga) ga('send','event','committee','summary-read-more');
});

// Committee detail meeting list filter
$cteDtlMtngsSearchInput.on('keyup', function(e) {
  typeAhead($cteDtlMtngsSearchInput,$cteDtlMtngsList,$cteDtlMtngsSearchResults,{ sort: true });
});
