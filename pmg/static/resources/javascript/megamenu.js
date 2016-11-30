/*global $ */
$(document).ready(function () {

    "use strict";

    $(".megamenu").mouseenter(function() {
      $(".committees-menulink").addClass("committees-menulink-hover");
      $(".megamenu").show();
    });

    $(".megamenu").mouseleave(function() {
      $(".committees-menulink").removeClass("committees-menulink-hover");
      $(".megamenu").hide();
    });

    $(".committees-menulink").mouseenter(function() {
      $(".megamenu").show();
    });

    $(".committees-menulink").mouseleave(function() {
      $(".megamenu").hide();
    });

});
