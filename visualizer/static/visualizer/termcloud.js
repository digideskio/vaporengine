/*
 *
 */

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
    // Add CSS classes for each audio_fragment_id
    var span_classes = [];
    for (var i = 0; i < this.model.attributes.audio_fragment_ids.length; i++) {
      span_classes.push("audio_fragment_span_" + this.model.attributes.audio_fragment_ids[i]);
    }
    this.$el.addClass(span_classes.join(" "));

    this.$el.text(termLabelText(this.model.attributes));

    return this;
  }
});

var TermCloud = Backbone.View.extend({
  el: '#termcloud',
  initialize: function() {
    this.listenTo(this.collection, 'sync', this.render);
  },
  render: function() {
    var $list = this.$('div.termcloud_terms').empty();

    this.collection.each(function(model) {
      var item = new TermCloudItemView({model: model});
      $list.append(item.render().$el);
    }, this);

    return this;
  }
});
