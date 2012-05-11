SELECTION = null;

(function($){
$(document).ready(function(){
    var annotation_container = $('#annotation-management');
    var img_container = $('#image-container');
    var add_container = $('#add-annotation');
    var pselect = $('#pselector');
    var add_button = add_container.find('button');
    var title = add_container.find('input');
    var text = add_container.find('textarea');
    var ann_container = $('#annotations');
    var annotations = ann_container.find('ul');
    var image = null;
    var sections_container = $('#section-management');
    var sections = sections_container.find('ul');
    var sectiontitle = $('#section-title');
    var sectionpage = $('#section-page');
    var add_section = $('#add-section');
    var add_section_button = add_section.find('.add');

    function reloadDV(){
        $('#DV-container').empty();
        window.initializeDV();
    }

    function setupPage(page){
        if(image != null){
            image.imgAreaSelect({remove: true});
            image.remove();
        }
        image = $('.DV-page-' + page + ' .DV-page img:first');
        image = image.clone();
        for(var i=0; i<window.documentData.pages; i++){
            var option = $('<option value="' + (i+1) + '">' + (i+1) + '</option>');
            if((i+1) == page){
                option[0].selected = true;
            }
            pselect.append(option);
        }

        /* add image */
        img_container.append(image);
        var width = image.width(), height = image.height();

        annotation_container.height(height);
        annotation_container.slideDown();
        image.imgAreaSelect({
            handles: true,
            onSelectEnd: function (img, selection) {
                SELECTION = selection;
            }
        });
    }

    pselect.change(function(){
        setupPage(parseInt($(this).val()));
    });

    function addToAnnotationList(title, page, id){
        annotations.append('<li>' + title + ' on page ' + page +  
                '(<a href="#" rel="' + id + '" page="' + page +
                    '" class="remove">Remove</a>)</li>');
    }

    add_button.click(function(){
        var titleval = title.val();
        var textval = text.val();
        if(!titleval || !textval || SELECTION == null){
            alert("You must fill out both title and text fields");
            return;
        }
        $.ajax({
            url: $('base').attr('href') + '/@@documentviewer-annotate',
            type: 'POST',
            data: {
                'action': 'addannotation',
                'title': titleval,
                'content': textval,
                'coord': SELECTION.y1 + ',' + SELECTION.x2 + ',' + SELECTION.y2 + ',' + SELECTION.x1,
                'page': pselect.val()
            },
            dataType: 'json',
            success: function(data){
                addToAnnotationList(data.title, pselect.val(), data.id);
                window.documentData.annotations.push({
                    location: {image: data.coord},
                    title: data.title,
                    id: data.id,
                    page: parseInt(pselect.val()),
                    access: 'public',
                    content: data.content});
                reloadDV();
                title.val('');
                text.val('');
                image.imgAreaSelect({hide: true});
            }
        });
    });

    $('#annotations a.remove').live('click', function(){
        var link = $(this);
        var id = parseInt($(this).attr('rel'));
        var page = parseInt($(this).attr('page'));
        $.ajax({
            url: $('base').attr('href') + '/@@documentviewer-annotate',
            type: 'POST',
            data: {
                'action': 'removeannotation',
                'id': id,
                'page': page
            },
            success: function(){
                link.parent().remove();
                //fix annotation in data also
                $.each(window.documentData.annotations, function(){
                    if(this.id == id && this.page == page){
                        window.documentData.annotations.pop(this);
                    }
                });
                reloadDV();
            }
        });
        return false;
    });

    $('#annotation-management .close,#section-management .close').click(function(){
        $(this).parent().slideUp();
        annotations.empty();
        title.val('');
        text.val('');
        sectiontitle.val('');
        sectionpage.val('');
        pselect.empty();
        sections.empty();
        $(this).parent().removeClass('open');
    });

    $('#manage-annotations').click(function(){
        /* Clear things out */
        if(sections_container.hasClass('open')){
            sections_container.find('.close').trigger('click');
        }else if(annotation_container.hasClass('open')){
            // already open
            return false;
        }
        annotation_container.addClass('open');

        /* setup page */
        var page = parseInt(window.currentDocument.elements.currentPage.html());
        setupPage(page);

        $.each(window.documentData.annotations, function(){
            addToAnnotationList(this.title, this.page, this.id);
        });

        return false;
    });

    function addToSectionList(title, page){
        sections.append('<li>' + title + ' for page ' + page +  
                '(<a href="#" rel="' + page + '" title="' + title +
                    '" class="remove">Remove</a>)</li>');
    }

    add_section_button.click(function(){
        var titleval = sectiontitle.val();
        var pageval = parseInt(sectionpage.val());
        $.ajax({
            url: $('base').attr('href') + '/@@documentviewer-annotate',
            type: 'POST',
            data: {
                'action': 'addsection',
                'title': titleval,
                'page': pageval
            },
            dataType: 'json',
            success: function(data){
                addToSectionList(titleval, pageval);
                window.documentData.sections.push({
                    title: titleval,
                    page: pageval});
                reloadDV();
                sectiontitle.val('');
                sectionpage.val('');
            }
        });
    });

    $('#sections a.remove').live('click', function(){
        var link = $(this);
        var titleval = $(this).attr('title');
        var pageval = parseInt($(this).attr('rel'));
        $.ajax({
            url: $('base').attr('href') + '/@@documentviewer-annotate',
            type: 'POST',
            data: {
                'action': 'removesection',
                'title': titleval,
                'page': pageval
            },
            success: function(){
                link.parent().remove();
                //fix annotation in data also
                $.each(window.documentData.sections, function(){
                    if(this.title == titleval && this.page == pageval){
                        window.documentData.sections.pop(this);
                    }
                });
                reloadDV();
            }
        });
        return false;
    });

    $('#manage-sections').click(function(){
        if(annotation_container.hasClass('open')){
            annotation_container.find('.close').trigger('click');
        }else if(sections_container.hasClass('open')){
            // already open
            return false;
        }
        sections_container.addClass('open');
        $.each(window.documentData.sections, function(){
            addToSectionList(this.title, this.page);
        });
        sections_container.slideDown();
        return false;
    });

    // $('#add-annotation').click(function(){
    //     var page = parseInt(window.currentDocument.elements.currentPage.html());
    //     var image = $('.DV-page-' + page + ' img:first');
    //     var container = $('<div id="annotate-container" />');
    //     var image = image.clone();
    //     container.append(image);
    //     $('body').append(container);
    //     var width = image.width(), height = image.height();
    //     image.imgAreaSelect({
    //         handles: true,
    //         onSelectEnd: function (img, selection) {
    //             SELECTION = selection;
    //         },
    //         x1: width/4, y1: height/4, x2: width/2, y2: height/2
    //     });

    //     var controls = $('<div id="annotate-controls" />');
    //     controls.append('<label>Title</label>');
    //     var title = $('<input type="text" />');
    //     controls.append(title);
    //     controls.append('<label>Text</label>');
    //     var text = $('<textarea></textarea>');
    //     controls.append(text);
    //     var add = $('<button class="add">Annotate</button>');
    //     add.click(function(){
    //         $.ajax({
    //             url: $('base').attr('href') + '/@@documentviewer-annotate',
    //             type: 'POST',
    //             data: {
    //                 'action': 'add',
    //                 'title': title.val(),
    //                 'content': text.val(),
    //                 'coord': SELECTION.y1 + ',' + SELECTION.x2 + ',' + SELECTION.y2 + ',' + SELECTION.x1,
    //                 'page': page
    //             },
    //             success: function(){
    //                 window.location.reload();
    //             }
    //         });
    //         return false;
    //     });
    //     controls.append(add);
    //     var close = $('<button id="close">Close Annotations</button>');
    //     close.click(function(){
    //         image.imgAreaSelect({remove: true});
    //         controls.remove();
    //         container.remove();
    //         return false;
    //     });
    //     controls.append(close);
    //     $('body').append(controls);
    //     return false;
    // });

    // $('#remove-annotations').click(function(){
    //     var page = parseInt(window.currentDocument.elements.currentPage.html());
    //     var image = $('.DV-page-' + page + ' img:first');
    //     var container = $('<div id="annotate-remove" />');
    //     var ann = $('<ul />');
    //     $.each(window.documentData.annotations, function(){
    //         if(this.page == page){
    //             ann.append('<li>' + this.title + 
    //                 '(<a href="#" rel="' + this.id + '" class="remove">Remove</a>)</li>');
    //         }
    //     });
    //     ann.find('.remove').click(function(){
    //         var link = $(this);
    //         $.ajax({
    //             url: $('base').attr('href') + '/@@documentviewer-annotate',
    //             type: 'POST',
    //             data: {
    //                 'action': 'remove',
    //                 'id': $(this).attr('rel'),
    //                 'page': page
    //             },
    //             success: function(){
    //                 link.parent().remove();
    //             }
    //         });
    //         return false;
    //     });
    //     container.append(ann);
    //     var close = $('<button id="close">Close</button>');
    //     close.click(function(){
    //         container.remove();
    //         window.location.reload();
    //         return false;
    //     });
    //     container.append(close);
    //     $('body').append(container);
    //     return false;
    // });

});
})(jQuery);