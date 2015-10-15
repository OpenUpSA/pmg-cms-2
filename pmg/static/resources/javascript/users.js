$(function() {
  // set select-all value on page load
  $(".select-all").each(function(){
    var select_all = $(this);
    var all_checked = true;
    var parent_list = select_all.closest('ul');
    parent_list.find(':checkbox.select-committee').each(function(){
      var tmp_checkbox = $(this);
      if(!tmp_checkbox.is(':checked'))
      {
        all_checked = false;
        return false; // break out of 'each' loop
      }
    });
    if(all_checked)
      select_all.prop("checked", true);
  });

  // toggle list of checkboxes with select-all
  $(".select-all").each(function(){
    var select_all = $(this);
    select_all.on('change', function(){
      var parent_list = select_all.closest('ul');
      if (select_all.is(':checked'))
      {
        // check all other boxes in the list
        parent_list.find(':checkbox.select-committee').prop('checked', true);
      }
      else
      {
        // un-check all other boxes in the list
        parent_list.find(':checkbox.select-committee').prop('checked', false);
      }
    });
  });

  $("input").on('change', function(){
    $(".submit-btn-container").each(function(){$(this).show();});
  });

  $(".remove-search-alert").on("click", function(e) {

    var btn = $(this),
        id = btn.data('id') || "",
        group = btn.closest('.grouped-search-alerts');

    $.post(
      '/user/saved-search/' + id + '/delete'
    ).done(function(resp) {
      btn.parents('.search-alert').remove();
      if (group.children('.search-alert').length === 0) {
        group.remove();
      }
      ga('send', 'event', 'user', 'remove-search-alert');
    });
  });

});

