
/* global WaveSurfer */


function WaveformVisualizer(visualizerID, customWavesurferSettings, customSettings) {
  // Use 'self' to give event handler access to current instance ('this')
  var self = this;

  var combinedWavesurferSettings, defaultWavesurferSettings;
  var defaultSettings;

  // Public member variables
  this.audio_events = [];
  this.visualizerID = visualizerID;
  this.wavesurfer = Object.create(WaveSurfer);

  // Initialization
  defaultWavesurferSettings = {
    container: document.querySelector('#' + this.visualizerID),
    dragSelection: false,
    normalize: true,
    progressColor: 'red',
    waveColor: 'pink',
  };
  combinedWavesurferSettings = $.extend({}, defaultWavesurferSettings, customWavesurferSettings);
  this.wavesurfer.init(combinedWavesurferSettings);
  this.wavesurfer.on('region-in', function(marker) {
    updateActiveDocumentForAudioEvent(marker);
  });

  defaultSettings = {
    controlsResizeCallback: undefined
  };
  this.settings = $.extend({}, defaultSettings, customSettings);

  // When browser window size changes, the GUI controls may also change in size
  $(window).resize(function() { callControlsResizeCallback(); });


  //// Public API

  this.addControls = function(parentElement) {
    var playerDiv = $('<div>')
      .attr('id', this.visualizerID + '_audio_control')
      .addClass('audio_control');

    var playPauseButton = $('<button>')
      .addClass('btn btn-primary btn-xs')
      .click(self.playPause)
      .html('<i class="glyphicon glyphicon-play"></i> / <i class="glyphicon glyphicon-pause"></i>');

    playerDiv.append(playPauseButton);

    parentElement.append(playerDiv);
  };

  this.addControlsAndLoadAudio = function(parentElement, audioSourceURL) {
    var playerDiv = $('<div>')
      .attr('id', self.visualizerID + '_audio_control')
      .addClass('audio_control');

    var playPauseButton = $('<button>')
      .addClass('btn btn-primary btn-xs')
      .click(self.playPause)
      .html('<i class="glyphicon glyphicon-play"></i> / <i class="glyphicon glyphicon-pause"></i>');

    playerDiv.append(playPauseButton);

    parentElement.append(playerDiv);

    this.loadURL(audioSourceURL);
  };

  // Remove UI information about current audio clip
  this.clear = function() {
    self.wavesurfer.seekTo(0.0);
    self.wavesurfer.empty();

    // If this WaveformVisualizer instance has an associated <div> that
    // contains buttons linking to source documents (utterances), remove
    // the buttons when we clear the waveform.
    var utteranceListDiv = $('#' + self.visualizerID + '_utterance_list');
    if (utteranceListDiv.length > 0) {
      // Delete existing buttons
      utteranceListDiv.html('');
      callControlsResizeCallback();
    }
  }

  this.loadAndPlayURL = function(audioSourceURL) {
    this.loadURL(audioSourceURL);
    this.wavesurfer.on('ready', function() {
      self.wavesurfer.play();
    });
  };

  this.loadURL = function(audioSourceURL) {
    var corpus, i, pseudotermID;

    this.wavesurfer.load(audioSourceURL);

    // If audio clip is a pseudoterm audio clip composed of multiple audio events,
    // add markers to waveform at audio event boundaries
    i = audioSourceURL.indexOf("/audio/pseudoterm/");
    if (i !== -1) {
      corpus = audioSourceURL.substr(8, i - 8);
      // Assumes that pseudotermID is a 24 character string
      pseudotermID = audioSourceURL.substr(i + 18, 24);

      $.getJSON('/corpus/' + corpus +"/audio/pseudoterm/" + pseudotermID + "_audio_events.json", function(audio_events) {
        updateAudioEvents(corpus, audio_events);
      });
    }
  };

  this.play = function() {
    rewindIfNecessary();
    self.wavesurfer.play();
  };

  this.pause = function() {
    self.wavesurfer.pause();
  };

  this.playPause = function() {
    rewindIfNecessary();
    self.wavesurfer.playPause();
  };


  //// Private functions, some of which are event handlers

  var callControlsResizeCallback = function() {
    if (self.settings.controlsResizeCallback) {
      self.settings.controlsResizeCallback();
    }
  };

  var resetActiveDocumentButtons = function() {
    var
      i,
      totalButtons,
      utteranceID;

    totalButtons = self.audio_events.length;
    for (i = 0; i < totalButtons; i++) {
      utteranceID = self.audio_events[i].utterance_id;
      $('#' + utteranceID + '_utterance_button')
        .addClass('btn-default')
        .removeClass('btn-info');
    }
  };

  var rewindIfNecessary = function() {
    // If waveform progress indicator is at end of clip, move progress
    // indicator back to beginning of clip
    if (Math.abs(self.wavesurfer.getDuration() - self.wavesurfer.getCurrentTime()) < 0.01) {
      resetActiveDocumentButtons();
      self.wavesurfer.seekTo(0.0);
    }
  };

  var updateActiveDocumentForAudioEvent = function(marker) {
    var
      previousUtteranceID = -1,
      utteranceID;

    // TODO: More sanity checks to verify that this handler is responsible for this region
    if (!self.audio_events[marker.id]) {
      return;
    }

    utteranceID = self.audio_events[marker.id].utterance_id;
    if (parseInt(marker.id) > 0) {
      previousUtteranceID = self.audio_events[parseInt(marker.id) - 1].utterance_id;
    }
    if (utteranceID !== previousUtteranceID && previousUtteranceID !== -1) {
      $('#' + previousUtteranceID + '_utterance_button')
        .addClass('btn-default')
        .removeClass('btn-info');
    }
    $('#' + utteranceID + '_utterance_button')
      .addClass('btn-info')
      .removeClass('btn-default');
  };

  var updateAudioEvents = function(corpus, audio_events) {
    var
      audio_events_per_utterance_id = {},
      audio_identifier_for_utterance_id = {},
      i,
      total_duration = 0.0,
      utterance_id,
      utteranceListDiv,
      utteranceSpan;

    self.audio_events = audio_events;
    self.wavesurfer.clearMarks();
    self.wavesurfer.clearRegions();

    for (i = 0; i < self.audio_events.length; i++) {
      self.wavesurfer.region({
        'color': 'blue',
        'id': i,
        'startPosition': total_duration,
        'endPosition': total_duration + self.audio_events[i].duration/100.0 - 0.01
      });
      total_duration += self.audio_events[i].duration / 100.0;
      self.wavesurfer.mark({
          'color': 'black',
          'id': i,
          'position': total_duration
      });

      utterance_id = self.audio_events[i].utterance_id;
      if (typeof(audio_events_per_utterance_id[utterance_id]) === 'undefined') {
        audio_events_per_utterance_id[utterance_id] = 0;
      }
      audio_events_per_utterance_id[utterance_id] += 1;
      audio_identifier_for_utterance_id[utterance_id] = self.audio_events[i].audio_identifier;
    }

    utteranceListDiv = $('#' + self.visualizerID + '_utterance_list');
    // Delete existing buttons
    utteranceListDiv.html('');
    // Add buttons for each distinct utterance
    for (utterance_id in audio_events_per_utterance_id) {
      utteranceSpan = $('<a>')
        .addClass('btn btn-default btn-xs')
        .attr('id', utterance_id + '_utterance_button')
        .attr('href', '/corpus/' + corpus +'/document/view/' + audio_identifier_for_utterance_id[utterance_id])
        .attr('role', 'button')
        .attr('style', 'margin-left: 0.5em; margin-right: 0.5em;')
        .html(audio_identifier_for_utterance_id[utterance_id] +
              ' <b>(x' + audio_events_per_utterance_id[utterance_id] + ')</b>');
      utteranceListDiv.append(utteranceSpan);
    }

    callControlsResizeCallback();
  };
}
