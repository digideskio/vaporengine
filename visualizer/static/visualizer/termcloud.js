/** TermCloud - a wordcloud of Terms - implemented with Backbone.js Models+Views
 *
 * There are two JS files for working with TermClouds - 'termcloud.js' and
 * 'termcloud_controls.js'.  The 'termcloud.js' file contains the Backbone.js
 * Model and View implementations.  The 'termcloud_controls.js' file implements
 * controls (buttons and menus) for manipulating TermClouds.  The control code
 * can "reach in" and manipulate TermCloud objects, but the TermCloud code
 * should not "reach out" (or depend on or have any awareness of) the control
 * code.
 *
 * If you are unfamiliar with Backbone.js, start by reading the documentation
 * and "Backbone, The Primer":
 *   http://backbonejs.org
 *   https://github.com/jashkenas/backbone/wiki/Backbone%2C-The-Primer
 *
 * Dependencies:
 *   Backbone.js
 *   jQuery
 *   Bootstrap    - TermCloud.render() uses Bootstrap tooltips
 */

/* globals Backbone */


var TermCloudItemModel = Backbone.Model.extend({
});

var TermCloudCollection = Backbone.Collection.extend({
  model: TermCloudItemModel,
  parse: function(data) {
    return data.terms;
  },
  url: function() {
    throw "You must override the Termcloud instance's 'url' property";
  },
});

var TermCloudItemView = Backbone.View.extend({
  tagName: 'span',
  className: 'wordcloud_token',

  render: function() {
    this.$el.attr('id', 'termcloud_item_' + this.model.attributes.term_id);

    // Add CSS classes for each audio_fragment_id
    var span_classes = [];
    for (var i = 0; i < this.model.attributes.audio_fragment_ids.length; i++) {
      span_classes.push('audio_fragment_span_' + this.model.attributes.audio_fragment_ids[i]);
    }
    this.$el.addClass(span_classes.join(' '));

    if (this.model.attributes.css_class) {
      this.$el.addClass(this.model.attributes.css_class);
    }

    this.$el.text(termLabelText(this.model.attributes));

    return this;
  }
});

var TermCloud = Backbone.View.extend({
  activeTermCloudItemModel: null,

  el: '#termcloud',

  events: {
    'click .wordcloud_token': 'onTermClick'
  },
  onTermClick: function(event) {
    // Update active term.  There can be only one active term at a time
    this.$('.active_wordcloud_token').removeClass('active_wordcloud_token');
    $(event.currentTarget).addClass('active_wordcloud_token');

    // Retrieve the model associated with the ItemView that was
    // clicked on, using the strategy described in this blog post:
    //   https://lostechies.com/derickbailey/2011/10/11/backbone-js-getting-the-model-for-a-clicked-element/
    var cid = $(event.currentTarget).data('cid');
    var model = this.collection.get(cid);

    // TermCloud needs to keep track of the active term when re-rendering
    this.activeTermCloudItemModel = model;

    // Trigger custom event
    this.trigger('click_model', model);
  },

  /** fontSizeFunction should take a TermCloudItemModel instance and returns a CSS font size value.
   */
  fontSizeFunction: function(termCloudItemModel) {
    return '1em';
  },

  initialize: function() {
    this.listenTo(this.collection, 'sync', this.updateFontSizeFunction);
    this.listenTo(this.collection, 'sync', this.render);
  },
  render: function() {
    this.trigger('render_start');

    // Remove all items from TermCloud
    var $list = this.$('div.termcloud_terms').empty();

    var collectionLength = this.collection.length;
    var termCloudItemList = [];

    // Add items to TermCloud
    this.collection.each(function(model) {
      var item = new TermCloudItemView({model: model});
      var item_el = item.render().$el;

      // Save Backbone.js client id (http://backbonejs.org/#Model-cid)
      // as jQuery data attribute.  We can use the cid to retrieve a
      // model from a collection, using:
      //   collection.get(cid)
      item_el.data('cid', model.cid);

      // Adjust size of word
      item_el.css('font-size', this.fontSizeFunction(model));

      var titleText = '';
      for (var i in this.sort_keys) {
        titleText += this.sort_keys[i].key_description + ': ' + model.attributes[this.sort_keys[i].key_name] + '\n';
      }
      item_el
        .attr('title', titleText);

      // Add a Bootstrap tooltip if the collection size is small enough.
      //
      // Adding a Bootstrap tooltip is a relatively expensive rendering
      // operation.  If the collection is too large, we skip adding the
      // tooltip, which makes the UI more responsive (though slightly
      // less attractive).
      if (collectionLength < 5000) {
        item_el
          .attr('data-placement', 'bottom')
          .attr('data-toggle', 'tooltip')
          .tooltip();
      }

      if (this.activeTermCloudItemModel === model) {
        item_el.addClass('active_wordcloud_token');
      }

      termCloudItemList.push(item_el);
    }, this);

    $list.append(termCloudItemList);

    this.trigger('render_stop');

    return this;
  },

  /** Updates the fontSizeFunction based on the attribute values of model instances in the TermCloudCollection
   */
  updateFontSizeFunction: function() {
    // Don't update fontSizeFunction if collection is empty
    if (this.collection.length === 0) {
      return;
    }

    var attribute = this.size_key;
    var modelWithMaxAttribute = this.collection.max(function(m) { return m.attributes[attribute]; });
    var maxAttributeValue = modelWithMaxAttribute.attributes[attribute];

    if (maxAttributeValue > 40) {
      // Scale font size using cube root
      this.fontSizeFunction = function(m) {
        return Math.cbrt(m.attributes[attribute]) + 'em';
      };
    }
    else {
      // Scale font size using square root
      this.fontSizeFunction = function(m) {
        return Math.sqrt(m.attributes[attribute]) + 'em';
      };
    }
  },

  size_key: '',
  sort_keys: []
});


function termLabelText(term) {
  if (term.label) {
    return term.label;
  }
  else {
    return 'T' + term.zr_term_index;
  }
}
