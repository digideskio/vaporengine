import collections
import json
import math
import os
import tempfile

from django.db.models import Count, Min
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
import pysox

from visualizer.models import (
    AudioFragment,
    Corpus,
    Document,
    DocumentTopic,
    DocumentTranscript,
    SituationFrameLabel,
    Term,
    TermCategory
)


def corpus_wordcloud(request, corpus_id):
    corpus = Corpus.objects.get(id=corpus_id)
    if corpus.protected_corpus and not request.user.is_authenticated():
        return redirect('/login/?next='+request.path)
    context = {'corpus': corpus}
    return render(request, "corpus_wordcloud.html", context)

def corpus_document_list(request, corpus_id):
    corpus = Corpus.objects.get(id=corpus_id)
    if corpus.protected_corpus and not request.user.is_authenticated():
        return redirect('/login/?next='+request.path)
    document_list = corpus.document_set.order_by('document_index')
    context = {'corpus': corpus, 'document_list': document_list}
    return render(request, "corpus_document_list.html", context)

def document(request, corpus_id, document_id):
    corpus = Corpus.objects.get(id=corpus_id)
    document = Document.objects.get(id=document_id)
    if corpus.protected_corpus and not request.user.is_authenticated():
        return redirect('/login/?next='+request.path)

    last_document_index = corpus.document_set.order_by('document_index').last().document_index
    if document.document_index == 0:
        previous_document_index = last_document_index
    else:
        previous_document_index = document.document_index - 1
    previous_document_id = corpus.document_set.filter(document_index=previous_document_index).first().id

    if document.document_index == last_document_index:
        next_document_index = 0
    else:
        next_document_index = document.document_index + 1
    next_document_id = corpus.document_set.filter(document_index=next_document_index).first().id

    document_transcript, _ = document.documenttranscript_set.get_or_create()

    context = {
        'corpus_id': corpus_id,
        'document_id': document_id,
        'document_audio_identifier': document.audio_identifier,
        'document_duration': document.duration_in_seconds(),
        'next_document_id': next_document_id,
        'previous_document_id': previous_document_id,
        'document_transcript': document_transcript,
    }
    return render(request, "document.html", context)

def document_audio_fragments_as_json(request, corpus_id, document_id):
    document = Document.objects.get(id=document_id)
    audio_fragments_json = []
    for audio_fragment in document.audiofragment_set.all():
        audio_fragments_json.append({
            'audio_fragment_id': audio_fragment.id,
            'start_offset': audio_fragment.start_offset,
            'end_offset': audio_fragment.end_offset
        })
    return JsonResponse(audio_fragments_json, safe=False)

def document_topic(request, corpus_id, document_topic_id):
    corpus = Corpus.objects.get(id=corpus_id)
    document_topic = DocumentTopic.objects.get(id=document_topic_id)

    if corpus.protected_corpus and not request.user.is_authenticated():
        return redirect('/login/?next='+request.path)
    context = {
        'corpus_id': corpus_id,
        'document_topic': document_topic,
    }
    return render(request, "document_topic.html", context)

def document_topic_json_for_document(request, corpus_id, document_id):
    corpus = Corpus.objects.get(id=corpus_id)
    document = Document.objects.get(id=document_id)
    document_topic_json = {}
    for dt in corpus.documenttopic_set.all():
        document_topic_json[dt.id] = {
            'label': dt.label,
            'description': dt.description
        }
    for dt in document.documenttopic_set.all():
        document_topic_json[dt.id]['selected'] = True
    return JsonResponse(document_topic_json)

@csrf_exempt
def document_topic_for_document_update(request, corpus_id, document_id):
    document = Document.objects.get(id=document_id)
    dt = DocumentTopic.objects.get(id=request.POST['document_topic_id'])
    if request.POST['action'] == 'add':
        SituationFrameLabel.objects.update_or_create(document=document, documenttopic=dt)
    else:
        SituationFrameLabel.objects.filter(document=document, documenttopic=dt).delete()
    return JsonResponse({})

@csrf_exempt
def document_transcript_update(request, corpus_id, document_id, document_transcript_id):
    document_transcript = DocumentTranscript.objects.get(id=document_transcript_id)
    if 'action' in request.POST and request.POST['action'] == 'update':
        document_transcript.text = request.POST['document_transcript_text']
        document_transcript.save()
        return JsonResponse({})
    else:
        return JsonResponse({'text': document_transcript.text})

def document_wav_file(request, corpus_id, document_id):
    document = Document.objects.get(id=document_id)
    if os.path.splitext(document.audio_path)[1] == '.wav':
        audio_file = open(document.audio_path, 'rb')
        response = HttpResponse(content=audio_file)
    else:
        # Convert non-WAV files to WAV files using pysox
        tmp_directory = tempfile.mkdtemp()
        tmp_filename = os.path.join(tmp_directory, 'converted.wav')

        infile = pysox.CSoxStream(document.audio_path)
        outfile = pysox.CSoxStream(tmp_filename, 'w', infile.get_signal())
        chain = pysox.CEffectsChain(infile, outfile)
        chain.flow_effects()
        infile.close()
        outfile.close()

        # Read in audio data from temporary file
        wav_data = open(tmp_filename, 'rb').read()

        # Clean up temporary files
        os.remove(tmp_filename)
        os.rmdir(tmp_directory)

        response = HttpResponse(content=wav_data)
    response['Content-Type'] = 'audio/wav'
    return response

def index(request):
    current_corpora = Corpus.objects.all()
    context = {'current_corpora': current_corpora}
    return render(request, "index.html", context)

def lorelei_situation_frames_json(request, corpus_id):
    corpus = Corpus.objects.get(id=corpus_id)
    situation_frames_json = []
    for document in corpus.document_set.all():
        for sfl in document.situationframelabel_set.all():
            sfl_json = {}
            sfl_json['DocumentID'] = document.audio_identifier
            sfl_json['Type'] = sfl.documenttopic.label
            sfl_json['TypeConfidence'] = 1.0
            if sfl.place:
                sfl_json['Place_KB_ID'] = sfl.place.kb_id
            situation_frames_json.append(sfl_json)
    pretty_json = json.dumps(situation_frames_json, indent=2, ensure_ascii=False, sort_keys=True) + u'\n'
    response = HttpResponse(content=pretty_json)
    response['Content-Type'] = 'application/json'
    return response

def place_english_autocomplete_json(request, corpus_id):
    corpus = Corpus.objects.get(id=corpus_id)
    term = request.GET['term']

    place_json = []
    for place in corpus.place_set.filter(english_name__icontains=term):
        place_json.append({
            'label': place.english_name,
            'value': place.kb_id
        })
    return JsonResponse(place_json, safe=False)

def place_native_autocomplete_json(request, corpus_id):
    corpus = Corpus.objects.get(id=corpus_id)
    term = request.GET['term']

    place_json = []
    for place in corpus.place_set.filter(native_name__icontains=term):
        place_json.append({
            'label': place.native_name,
            'value': place.kb_id
        })
    return JsonResponse(place_json, safe=False)

def term_audio_fragments_as_json(request, corpus_id, term_id):
    term = Term.objects.get(id=term_id)

    audio_fragments_json = []
    for audio_fragment in term.audiofragment_set.all():
        audio_fragments_json.append({
            'duration': audio_fragment.duration,
            'audio_identifier': audio_fragment.document.audio_identifier,
            'document_id': audio_fragment.document_id,
            'document_index': audio_fragment.document.document_index
        })
    return JsonResponse(audio_fragments_json, safe=False)

@csrf_exempt
def term_category_for_term_update(request, corpus_id, term_id):
    term  = Term.objects.get(id=term_id)
    tc = TermCategory.objects.get(id=request.POST['term_category_id'])
    if request.POST['action'] == 'add':
        term.termcategory_set.add(tc)
    else:
        term.termcategory_set.remove(tc)
    return JsonResponse({})

def term_category_json_for_term(request, corpus_id, term_id):
    corpus = Corpus.objects.get(id=corpus_id)
    term = Term.objects.get(id=term_id)
    term_category_json = {}
    for tc in corpus.termcategory_set.all():
        term_category_json[tc.id] = { 'name': tc.name }
    for tc in term.termcategory_set.all():
        term_category_json[tc.id]['selected'] = True
    return JsonResponse(term_category_json)


@csrf_exempt
def term_update(request, term_id):
    request_data = json.loads(request.body)
    term = Term.objects.get(id=term_id)
    term.label = request_data['label']
    term.save()
    return JsonResponse({})

def term_wav_file(request, corpus_id, term_id):
    corpus = Corpus.objects.get(id=corpus_id)
    term = Term.objects.get(id=term_id)
    sox_signal_info = pysox.CSignalInfo(corpus.audio_rate, corpus.audio_channels, corpus.audio_precision)

    # TODO: Allow number of audio fragments to be specified as parameter, instead
    #       of hard-coded to 10
    audio_fragments = term.audiofragment_set.all()[:10]

    # Create a temporary directory
    tmp_directory = tempfile.mkdtemp()
    tmp_filename = os.path.join(tmp_directory, 'combined_clips.wav')

    # The first argument to CSoxStream must be a filename with a '.wav' extension.
    #
    # If the output file does not have a '.wav' extension, pysox will raise
    # an "IOError: No such file" exception.
    outfile = pysox.CSoxStream(tmp_filename, 'w', sox_signal_info)

    for audio_fragment in audio_fragments:
        START_OFFSET = bytes("%f" % (audio_fragment.start_offset / 100.0))
        DURATION = bytes("%f" % (audio_fragment.duration / 100.0))
        input_filename = audio_fragment.document.audio_path
        infile = pysox.CSoxStream(input_filename)
        chain = pysox.CEffectsChain(infile, outfile)
        chain.add_effect(pysox.CEffect('trim', [START_OFFSET, DURATION]))
        chain.flow_effects()
        infile.close()

    outfile.close()

    # Read in audio data from temporary file
    wav_data = open(tmp_filename, 'rb').read()

    # Clean up temporary files
    os.remove(tmp_filename)
    os.rmdir(tmp_directory)

    response = HttpResponse(content=wav_data)
    response['Content-Type'] = 'audio/wav'
    return response

def wordcloud_json_for_corpus(request, corpus_id):
    corpus = Corpus.objects.get(id=corpus_id)

    # Use Django's annotate() to compute total # of Documents and AudioFragments associated with each Term.
    #
    # With annotate(), we can compute the # of AudioFragments associated with each Term in a Corpus using
    # just a single SQL query for the entire Corpus.  This is an order-of-magnitude faster than making
    # a separate SQL call for each Term in the Corpus by calling term.total_audio_fragments() in a for loop.
    terms = corpus.terms().annotate(Count('audiofragment'), Count('audiofragment__document', distinct=True)).order_by('-audiofragment__count')[0:100]

    # Create a mapping from each Term ID to the corresponding list of AudioFragment IDs, using a single SQL query.
    #
    # This is an order of magnitude faster than using a separate SQL query for each Term by calling
    # term.audio_fragment_ids() in a for loop.
    term_audiofragment_id_pairs = AudioFragment.objects.filter(document__corpus_id=corpus_id).values_list('term_id', 'id')
    term_id_to_audiofragment_ids = collections.defaultdict(list)
    for (term_id, audiofragment_id) in term_audiofragment_id_pairs:
        term_id_to_audiofragment_ids[term_id].append(audiofragment_id)

    terms_json = []
    for term in terms:
        terms_json.append({
            'label': term.label,
            'zr_term_index': term.zr_term_index,

            'id': term.id,
            'term_id': term.id,
            'corpus_id': corpus_id,

            'audio_fragment_ids': term_id_to_audiofragment_ids[term.id],
            'total_audio_fragments': term.audiofragment__count,
            'total_documents': term.audiofragment__document__count,
        })
    response = HttpResponse(content=json.dumps({
        'terms': terms_json
    }))
    response['Content-Type'] = 'application/json'
    return response

def wordcloud_params_for_corpus(request):
    response = HttpResponse(content=json.dumps({
        'default_size_key': 'total_documents',
        'size_keys': [
            {'key_name': 'total_documents', 'key_description': 'Documents appeared in'},
            {'key_name': 'total_audio_fragments', 'key_description': 'Occurrences in corpus'},
        ],
        'default_sort_key': 'total_audio_fragments',
        'sort_keys': [
            {'key_name': 'total_documents', 'key_description': 'Documents appeared in'},
            {'key_name': 'label', 'key_description': 'Label'},
            {'key_name': 'total_audio_fragments', 'key_description': 'Occurrences in corpus'}
        ],
    }))
    response['Content-Type'] = 'application/json'
    return response

def wordcloud_json_for_document(request, corpus_id, document_id):
    corpus = Corpus.objects.get(id=corpus_id)
    document = Document.objects.get(id=document_id)
    total_documents = corpus.document_set.count()

    terms = document.associated_terms().annotate(audio_fragments_in_document=Count('audiofragment', distinct=True),
                                                 first_audiofragment_start_offset=Min('audiofragment__start_offset'))

    # Create a mapping from Term ID to # of Documents Term appears in, using a single SQL query
    term_id_and_document_counts = corpus.terms().annotate(document_count=Count('audiofragment__document', distinct=True)).values_list('id', 'document_count')
    term_id_to_document_count = {}
    for (term_id, document_count) in term_id_and_document_counts:
        term_id_to_document_count[term_id] = document_count

    # Create a mapping from each Term ID to the corresponding list of AudioFragment IDs, using a single SQL query.
    term_audiofragment_id_pairs = AudioFragment.objects.filter(document__corpus_id=corpus_id).values_list('term_id', 'id')
    term_id_to_audiofragment_ids = collections.defaultdict(list)
    for (term_id, audiofragment_id) in term_audiofragment_id_pairs:
        term_id_to_audiofragment_ids[term_id].append(audiofragment_id)

    terms_json = []
    for term in terms:
        tf_idf = term.audio_fragments_in_document * math.log(total_documents / (1.0 + term_id_to_document_count[term.id]))
        terms_json.append({
            'label': term.label,
            'zr_term_index': term.zr_term_index,

            'id': term.id,
            'term_id': term.id,
            'corpus_id': corpus_id,

            # Unoptimized code:
            #   'audio_fragment_ids': list(term.audio_fragment_ids()),
            'audio_fragment_ids': term_id_to_audiofragment_ids[term.id],

            # Unoptimized code:
            #   'first_start_offset_in_document': term.first_start_offset_in_document(document),
            'first_start_offset_in_document': term.first_audiofragment_start_offset/100.0,

            'tf_idf': tf_idf,

            # Unoptimized code:
            #   'total_audio_fragments': term.total_audio_fragments(),
            'total_audio_fragments': len(term_id_to_audiofragment_ids[term.id]),

            # Unoptimized code:
            #   'total_audio_fragments_in_document': term.total_audio_fragments_in_document(document),
            'total_audio_fragments_in_document': term.audio_fragments_in_document,

            # Unoptimized code:
            #   'total_documents': term.total_documents(),
            'total_documents': term_id_to_document_count[term.id],
        })
    response = HttpResponse(content=json.dumps({
        'terms': terms_json
    }))
    response['Content-Type'] = 'application/json'
    return response

def wordcloud_params_for_document(request):
    response = HttpResponse(content=json.dumps({
        'default_size_key': 'total_documents',
        'size_keys': [
            {'key_name': 'total_documents', 'key_description': 'Documents appeared in'},
            {'key_name': 'total_audio_fragments', 'key_description': 'Occurrences in corpus'},
            {'key_name': 'total_audio_fragments_in_document', 'key_description': 'Occurences in document'},
            {'key_name': 'tf_idf', 'key_description': 'TF-IDF'},
        ],
        'default_sort_key': 'first_start_offset_in_document',
        'sort_keys': [
            {'key_name': 'total_documents', 'key_description': 'Documents appeared in'},
            {'key_name': 'first_start_offset_in_document', 'key_description': 'First appearance'},
            {'key_name': 'label', 'key_description': 'Label'},
            {'key_name': 'total_audio_fragments', 'key_description': 'Occurrences in corpus'},
            {'key_name': 'total_audio_fragments_in_document', 'key_description': 'Occurences in document'},
            {'key_name': 'tf_idf', 'key_description': 'TF-IDF'},
        ],
    }))
    response['Content-Type'] = 'application/json'
    return response

def wordcloud_json_for_document_topic(request, corpus_id, document_topic_id):
    corpus = Corpus.objects.get(id=corpus_id)
    document_topic = DocumentTopic.objects.get(id=document_topic_id)
    total_documents = corpus.document_set.count()

#    terms = document_topic.terms().annotate(Count('audiofragment'), Count('audiofragment__document', distinct=True))
    terms = document_topic.terms_with_document_topic_info().annotate(Count('audiofragment'), Count('audiofragment__document', distinct=True))

    # Create a mapping from each Term ID to the corresponding list of AudioFragment IDs, using a single SQL query.
    term_audiofragment_id_pairs = AudioFragment.objects.filter(document__corpus_id=corpus_id).values_list('term_id', 'id')
    term_id_to_audiofragment_ids = collections.defaultdict(list)
    for (term_id, audiofragment_id) in term_audiofragment_id_pairs:
        term_id_to_audiofragment_ids[term_id].append(audiofragment_id)

    term_id_to_dttis = collections.defaultdict(list)
    for dtti in document_topic.documenttopicterminfo_set.all():
        term_id_to_dttis[dtti.term_id].append(dtti)

    category_name_to_index = {}
    for index, category in enumerate(document_topic.term_info_categories()):
        category_name_to_index[category] = index

    terms_json = []
    for term in terms:
        term_json = {
            'label': term.label,
            'zr_term_index': term.zr_term_index,

            'css_class': '',

            'id': term.id,
            'term_id': term.id,
            'corpus_id': corpus_id,

            'audio_fragment_ids': term_id_to_audiofragment_ids[term.id],

            'total_audio_fragments': term.audiofragment__count,
            'total_documents': term.audiofragment__document__count,
        }
        if term.id in term_id_to_dttis:
            for dtti in term_id_to_dttis[term.id]:
                term_json['css_class'] += 'term_info_category_%d ' % category_name_to_index[dtti.category]
                term_json['term_info_' + dtti.category] = dtti.score
        terms_json.append(term_json)
    response = HttpResponse(content=json.dumps({
        'terms': terms_json
    }))
    response['Content-Type'] = 'application/json'
    return response

def wordcloud_params_for_document_topic(request, document_topic_id):
    document_topic = DocumentTopic.objects.get(id=document_topic_id)
    wordcloud_params = {
        'default_size_key': 'total_documents',
        'size_keys': [
            {'key_name': 'total_documents', 'key_description': 'Topic Documents appeared in'},
            {'key_name': 'total_audio_fragments', 'key_description': 'Occurrences in Topic Documents'},
        ],
        'default_sort_key': 'total_audio_fragments',
        'sort_keys': [
            {'key_name': 'total_documents', 'key_description': 'Topic Documents appeared in'},
            {'key_name': 'label', 'key_description': 'Label'},
            {'key_name': 'total_audio_fragments', 'key_description': 'Occurrences in Topic Documents'}
        ],
    }
    for category in document_topic.term_info_categories():
        wordcloud_params['sort_keys'].append({
            'key_name': 'term_info_' + category,
            'key_description': category,
        })
        # Set default_sort_key to sort by category IFF a category exists
        wordcloud_params['default_sort_key'] = 'term_info_' + category
    response = HttpResponse(content=json.dumps(wordcloud_params))
    response['Content-Type'] = 'application/json'
    return response
