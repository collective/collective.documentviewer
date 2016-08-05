
require([
  'jquery',
  'mockup-patterns-base',
  'mockup-utils'
], function($, Base, utils) {
  "use strict";

  var DocumentViewer = Base.extend({
    name: 'documentviewer',
    trigger: '.pat-documentviewer',
    parser: 'mockup',
    defaults: {
    },
    init: function() {
      var that = this;

      var options = $.extend({}, true, that.options, {
        container: that.$el[0]
      });
      delete options.data;

      if($(window).width() < 800){
        options.sidebar = false;
      }
      DV.load(that.options.data, options);
    }
  });

  return DocumentViewer;
});
