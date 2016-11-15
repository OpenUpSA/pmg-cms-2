var currentDate = new Date();
// Committee list DOM
var $cteList = $('.cte-list');
var $cteListItems = $('.cte-list .tab-pane.active .committee');
var $cteListSearchInput = $('.cte-list-search input');
var $cteListSearchResults = $('.cte-list-search-results');
var $cteListNavItem = $('.cte-list-nav a, .cte-list-nav-mobile option');
var $cteListUserFollowing = $('.cte-list-user-following ul');
var $cteListFollowCommittee = $('.cte-follow-committee');
var $noCteFollowedMsg = $('.no-committees-followed');
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
var $lunrDict = $('.lunr-dict');
var $lunrDictItems = null;
// megaMenu
var $megaMenuFollowing = $('.top-links .committee-megamenu-table');
var $megaMenuFollowingMobile = $('.top-links-mobile .committee-megamenu-table');

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

      $resultsListLeft.empty();
      $resultsListRight.empty();

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
      $resultsList.empty()
        .append(results);
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
      return $lunrDictItems.filter(function(i,item) {
        return $(item).attr('data-id') == result.ref;
      })[0];
    });

    renderSearchResults(results,$list,$res,params);
  }
}, 200);

var indexItems = function() {
  var isCteDtlMeetings = $lunrDict.hasClass('cte-dtl-meetings-list');

  $lunrDictItems = $('.lunr-dict .item:not(.exclude), .lunr-dict .active .item:not(.exclude)').clone();

  index = lunr(function() {
    var self = this;

    self.field('name');

    // On the committee detail page, we also have the option to search meetings
    // by date
    if(isCteDtlMeetings) {
      self.field('date');
    }

    self.ref('id');
  });

  $lunrDictItems.each(function(i,item) {
    var $item = $(item);
    var indexItem = {
      id: $item.attr('data-id')
    };

    // Here we take lunr's index fields and add them as properties to each item.
    // We expect an item to have child elements that have class names that
    // match these fields.
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

$cteList.on('change', '.cte-follow-committee input[type=checkbox]', function(e) {
    var $targetItem = $(e.target).closest('li');
    var id = $targetItem.attr('data-id');
    var $listItem = $('.cte-items [data-id=' + id + ']');
    var $listItemForm = $listItem.find('form');
    var $followedItem = $('[data-id=' + id + '][data-follow-list="true"]');
    var data = $listItemForm.serialize();

    $.post($targetItem.find('form').attr('action'), data, function(res) {
      if(!!$targetItem.attr('data-following')) {
        $followedItem.remove();
        $listItem.removeAttr('data-following');
        $listItemForm.attr('action','/user/follow/committee/' + id)
          .find('input[type=checkbox]')
          .prop('checked',false);
      } else {
        $listItem.attr('data-following','true');
        $listItemForm.attr('action','/user/unfollow/committee/' + id);
        $cteListUserFollowing.append($listItem.clone().attr('data-follow-list','true'));

        // Attach to megamenu
        var name = $listItem.find('.name').html();
        var $premium = $listItem.find('.premium').length ? '<span class="premium"><i class="fa fa-key"></i> Premium</span>' : '';
        var $megaMenuItem = $('<li data-id="' + id + '" data-follow-list="true"><a href="/committee/' + id + '">' + name + '</a>' + $premium + '</li>');
        var $megaMenuItems = $megaMenuFollowing.find('li');

        $megaMenuItems.each(function(i) {
          var thisName = $(this).find('a').html();
          var nextName = $($megaMenuItems[i + 1]).find('a').html();
          console.log(name,thisName,nextName,name < thisName,name < nextName);
          if(name <= thisName) {
            console.log('true');
            $megaMenuItem.insertBefore($megaMenuItems[i]);
            return false;
          } else if((thisName < name && nextName >= name) || i == $megaMenuItems.length - 1) {
            $megaMenuItem.insertAfter($megaMenuItems[i]);
            return false;
          }
        });

      /*  $megaMenuItems.sort(function(a,b) {
          if($(a).find('a').html() < $(b).find('a').html()) {
            return -1;
          } else {
            return 1;
          }

          return 0;
        });

        var $items = $megaMenuItems.detach();

        $megaMenuFollowingMobile.empty()
          .append($items);*/
      }

      if($cteListUserFollowing.find('li').length) {
        $noCteFollowedMsg.hide();
      } else {
        $noCteFollowedMsg.show();
      }
    });
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
