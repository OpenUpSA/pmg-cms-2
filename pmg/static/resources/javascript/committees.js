var currentDate = new Date();
// Committee list DOM
var $cteList = $('.cte-list');
var $cteListItems = $('.cte-list .tab-pane.active .committee');
var $cteListSearchInput = $('.cte-list-search input');
var $cteListSearchResults = $('.cte-list-search-results');
var $cteListNavItem = $('.cte-list-nav a, .cte-list-nav-mobile option');
// Committee details DOM
var $cteDtlNavItem = $('.cte-dtl-meetings-nav a, .cte-dtl-meetings-nav-mobile option');
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
// Lunr elements
var $lunrDict = null;

// Set up lunr index for filtering
var index = null;

// Committee list page methods and handlers
var clearSearchResult = function($list,$res,params) {
  var $resultsList = $res.find('.results-list');

  $res.find('.no-results')
    .hide();

  if(!!params && params.twoCol) {
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

var renderSearchResults = function(results,$list,$res,params) {
  var resultsCount = results.length;
  var $noResults = $res.find('.no-results');
  var $resultsList = $res.find('.results-list');

  //clearSearchResult($list,$res,params);

  showingSearchResult = true;

  $list.hide();
  $noResults.hide();

  if(!!resultsCount) {
    $resultsList.show();

    if(!!params && params.sort) {
      results.sort(function(a,b) {
        return new Date($(b).find('.date').text()) - new Date($(a).find('.date').text());
      });
    }

    if(!!params && params.twoCol) {
      var $resultsListLeft = $resultsList.find('.left');
      var $resultsListRight = $resultsList.find('.right');

      if(resultsCount > 20) {
        if(resultsCount < 40) {
          $resultsListLeft.append(results.slice(0,19));
          $resultsListRight.append(results.slice(20));
        } else {
          $resultsListLeft.append(results.slice(0,resultsCount / 2 - 1));
          $resultsListRight.append(results.slice(resultsCount / 2));
        }
      } else {
        $resultsListLeft.append(results);
      }
    } else {
      $resultsList.append(results);
    }
  } else {
    $resultsList.hide();
    $noResults.show();
  }
};

var filterMeetings = function($target) {
  var filter = $target.attr('data-filter');
  var $table = $('#m-' + filter);

  $cteDtlListTables.hide();
  $table.fadeIn({ duration: 250, easing: 'linear' });

  return filter;
}

var searchIndex = debounce(function(query,$list,$res,params) {
  var results = null;

  if(!query.length)  {
    clearSearchResult($list,$res,params);
    return;
  } else {
    results = index.search(query).map(function(result) {
      return $lunrDict.filter(function(i,item) {
        return $(item).attr('data-id') == result.ref;
      })[0];
    });

    renderSearchResults(results,$list,$res,params);
  }
}, 200);

var indexItems = function() {
  $lunrDict = $('.lunr-dict .active .item:not(.exclude)').clone();

  index = lunr(function() {
    var self = this;

    self.ref('id');

    Array.prototype.forEach.call($($lunrDict[0])[0].children, function(child) {
      var $child = $(child);

      if(!$child.hasClass('exclude')) self.field($child.attr('class').split(' ')[0]);
    });
  });

  $lunrDict.each(function(i,item) {
    var $item = $(item);
    var indexItem = {
      id: $item.attr('data-id')
    };

    index._fields.forEach(function(field) {
      var name = field.name;

      indexItem[name] = $item.find('.' + name).text();
    });

    index.add(indexItem);
  });
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

  indexItems();
  $cteListSearchInput.val('');

  if(showingSearchResult) clearSearchResult($cteList,$cteListSearchResults,{ twoCol: true });
});

$cteListSearchInput.on('keyup', function(e) {
  searchIndex($(e.target).val(), $cteList, $cteListSearchResults, { twoCol: true });
});

// Committee detail page handlers
$cteDtlNavItem.on('click', indexItems);

$cteDtlFilterSelect.on('change', function(e) {
  filterMeetings($('option:selected',this));
  $cteDtlMtngsSearchInput.val('');

  clearSearchResult($cteDtlMtngsList,$cteDtlMtngsSearchResults);
  $cteDtlMtngsList.show();
});

$cteDtlFilterSelect.on('focus', function() {
  this.selectedIndex = -1;
});

$cteDtlFilterSelect.on('blur', function() {
  if(this.selectedIndex === -1) {
    this.selectedIndex = 0;
  }
});

// Committee detail meeting list filter
$cteDtlMtngsSearchInput.on('keyup', function(e) {
  searchIndex($(e.target).val(),$cteDtlMtngsList,$cteDtlMtngsSearchResults, { sort: true });
});

// Generate initial index
indexItems();
