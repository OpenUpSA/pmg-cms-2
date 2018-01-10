var currentDate = new Date();
// Committee list DOM
var $cteList = $('.cte-list');
var $cteGetAlerts = $('.cte-get-alerts');
var $cteListSearchInput = $('.cte-list-search input');
var $cteListSearchResults = $('.cte-list-search-results');
var $cteListUserFollowing = $('.cte-list-user-following ul');
var $cteListFollowCommittee = $('.cte-follow-committee');
var $noCteFollowedMsg = $('.no-committees-followed');
// Committee details DOM
var $cteDtlNavItem = $('.cte-dtl-meetings-nav a, .cte-dtl-meetings-nav-mobile option');
var $cteDtlNavMobileSelect = $('.cte-dtl-meetings-nav-mobile select');
var $cteDtlFilterSelect = $('.cte-dtl-meetings-filter select');
var $cteDtlFilterSelectDown = $('.cte-dtl-meetings-filter.down select');
var $cteDtlListTables = $('.cte-dtl-meetings-list .table');
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
var $megamenu = $('.megamenu');

// Set up lunr index for filtering
var index = null;

// Committee list page methods and handlers
function clearSearchResult($list,$res,params) {
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
function debounce(func, wait, immediate) {
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
}

function getParameterByName(name, url) {
    if (!url) url = window.location.href;
    name = name.replace(/[\[\]]/g, "\\$&");
    var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, " "));
}

function renderSearchResults(results,$list,$res,params) {
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
}

function filterCommitteeMeetings(q) {
  var filter = $cteDtlFilterSelect.find('option[value="' + q + '"]').attr('data-filter');
  var $table = $('#m-' + filter);

  $cteDtlListTables.hide();
  $table.fadeIn({ duration: 250, easing: 'linear' });

  $cteDtlMtngsSearchInput.val('');

  clearSearchResult($cteDtlMtngsList,$cteDtlMtngsSearchResults);
  $cteDtlMtngsList.show();

  $cteDtlFilterSelect.val(q);
}

function searchCommitteeMeetings(q) {
  searchIndex(q, $cteDtlMtngsList, $cteDtlMtngsSearchResults, { sort: true });
}

function updateUrl() {
  // update the url based on the cte meeting search params
  var q = encodeURIComponent($cteDtlMtngsSearchInput.val()),
      filter = encodeURIComponent($cteDtlFilterSelect.val()),
      url;

  if (q) {
    url = "q=" + q;
  } else if (filter) {
    url = "filter=" + filter;
  }

  history.pushState(null, "", "?" + url);
}
var updateUrlDelayed = debounce(updateUrl, 1000);

function unpackUrl() {
  // unpack the cte meeting search details from the url
  var q = getParameterByName('q', location.search),
      filter = getParameterByName('filter', location.search);

  if (q) {
    $cteDtlMtngsSearchInput.val(q);
    searchCommitteeMeetings(q);
  } else if (filter) {
    $cteDtlFilterSelect.val(filter);
    filterCommitteeMeetings(filter);
  }
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

function indexItems() {
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

function committeeFollowChange(e) {
    var $target = $(e.target);
    var $targetItem = $target.closest('li');
    var id = $targetItem.attr('data-id');
    var $listItem = $('.cte-items [data-id=' + id + ']');
    var $cteListUserFollowingItems = $cteListUserFollowing.find('li');
    var $listItemForm = $listItem.find('form');
    var $followedItem = $('[data-id=' + id + '][data-follow-list="true"]');
    var data = $listItemForm.serialize();
    var actionUrl = $targetItem.find('form').attr('action');

    if(!!$targetItem.attr('data-following')) {
      $followedItem.remove();
      $listItem.removeAttr('data-following');
      $listItemForm.attr('action','/user/follow/committee/' + id)
        .find('input[type=checkbox]')
        .prop('checked', false);
    } else {
      // Attach to megamenu
      var name = $listItem.find('.name').html();
      var isPremium = $listItem.find('.premium').length;

      $listItem.attr('data-following','true');
      $listItemForm.attr('action','/user/unfollow/committee/' + id)
        .find('input[type=checkbox]')
        .prop('checked', true);

      insertIntoDOMList($cteListUserFollowingItems,$listItem.clone().attr('data-follow-list', 'true'), $cteListUserFollowing, name, 'a');
    }

    if($cteListUserFollowing.find('li').length) {
      $noCteFollowedMsg.hide();
    } else {
      $noCteFollowedMsg.show();
    }

    $.post(actionUrl, data, mmUpdate);
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
$('.cte-list-nav a, .cte-list-nav-mobile option').on('click', function(e) {
  e.preventDefault();

  indexItems();
  $cteListSearchInput.val('');

  if(showingSearchResult) clearSearchResult($cteList,$cteListSearchResults,{ twoCol: true });
});

$cteListSearchInput.on('keyup', function(e) {
  searchIndex($(e.target).val(), $cteList, $cteListSearchResults, { twoCol: true });
});

function insertIntoDOMList($list,$item,$container,name,nameTag) {
  if(!!$list.length) {
    $list.each(function(i) {
      var thisName = $(this).find(nameTag).html();
      var nextName = $($list[i + 1]).find(nameTag).html();

      if(name <= thisName) {
        $item.insertBefore($list[i]);
        return false;
      } else if((thisName < name && nextName >= name) || i == $list.length - 1) {
        $item.insertAfter($list[i]);
        return false;
      }
    });
  } else {
    $container.append($item);
  }
}

function mmUpdate() {
  $.get('/user/megamenu/', function(result) {
    $megamenu.empty().html(result);
  }, 'html');
}

$('.cte-signup-box').on('change','.cte-follow-committee input[type=checkbox]', function(e) {
  var $target = $(e.target);
  var $form = $target.closest('form');
  var data = $form.serialize();
  var url = $form.attr('action').split('/');
  var actionUrl = url.join('/');
  var id = url[url.length - 1];
  var isFollowing = url[2] == 'unfollow';

  if(isFollowing) {
    $('.mm-committees-list [data-id=' + id + '][data-follow-list="true"]').remove();

    $form.attr('action','/user/follow/committee/' + id)
      .find('input[type=checkbox]')
      .prop('checked', false);

    $cteGetAlerts.find('input[type=checkbox]')
      .prop('checked', false);
  } else {
    var name = $('.committee-name').html();
    var isPremium = $('.premium').length;

    $form.attr('action','/user/unfollow/committee/' + id)
      .find('input[type=checkbox]')
      .prop('checked', true);

      $cteGetAlerts.find('input[type=checkbox]')
        .prop('checked', true);
  }

  $.post(actionUrl, data, mmUpdate);
});

$cteList.on('change', '.cte-follow-committee input[type=checkbox]', committeeFollowChange);
$cteListSearchResults.on('change', '.cte-follow-committee input[type=checkbox]', committeeFollowChange);

// Committee detail page handlers
$cteDtlNavItem.on('click', indexItems);

$cteDtlFilterSelect.on('change', function(e) {
  filterCommitteeMeetings($(this).val());
  updateUrl();
});

$cteDtlFilterSelectDown.on('change', function(e) {
  $('html, body').scrollTop($(".cte-dtl-meetings").offset().top);
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
  searchCommitteeMeetings($(e.target).val());
  updateUrlDelayed();
});

// Generate initial index
indexItems();

if ($('body').hasClass('committee_detail')) {
  window.addEventListener('popstate', unpackUrl);
  unpackUrl();
}

$(document).ready(function() {
  if (window.location.href.indexOf("#NA") > -1) {
    $(".tab-switch-nat").click();
  } else if (window.location.href.indexOf("#NCOP") > -1) {
    $(".tab-switch-ncp").click();
  } else if (window.location.href.indexOf("#Joint") > -1) {
    $(".tab-switch-jnt").click();
  } else if (window.location.href.indexOf("adhoc") > -1) {
    $(".tab-switch-adhoc").click();
  } else if (window.location.href.indexOf("prov") > -1) {
    $(".tab-switch-prov").click();
  }
});