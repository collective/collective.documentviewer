SELECTION = null;

(function($){
$(document).ready(function(){
    'use strict';

    var baseUrl = $('base').attr('href');
    if(!baseUrl){
        baseUrl = $('body').attr('data-base-url');
    }
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
    var right_container = $('#right-container');

    function reloadDV(){
        $('#DV-container').empty();
        window.initializeDV();
    }

    function setupPage(page){
        if(image != null){
            image.imgAreaSelect({remove: true});
            image.remove();
        }
        var url = window.documentData.resources.page.image.replace('{size}', 'normal').replace('{page}', page);
        image = $('<img src="' + url + '" />');
        for(var i=0; i<window.documentData.pages; i++){
            var num = i + 1;
            if(pselect.find('[value="' + num + '"]').length > 0){
                continue;
            }
            var option = $('<option value="' + num + '">' + num + '</option>');
            if(num == page){
                option[0].selected = true;
            }
            pselect.append(option);
        }

        /* add image */
        img_container.append(image);
        var loadingImage = new Image();
        loadingImage.src = image.attr("src");
        $(loadingImage).load(function(){
            var height = loadingImage.height;
            annotation_container.height(height);
            right_container.height(height - 20);
            image.imgAreaSelect({
                handles: true,
                onSelectEnd: function (img, selection) {
                    SELECTION = selection;
                }
            });
            annotation_container.show();
        });
    }

    pselect.change(function(){
        setupPage(parseInt($(this).val()));
    });

    function addToAnnotationList(title, page, id){
        annotations.append('<li>' + title +' '+window.dv_translated_label_on_page+' '+page+
                ' (<a href="#" rel="' + id + '" page="' + page +
                    '" class="remove">'+window.dv_translated_label_remove+'</a>)</li>');
    }

    function clearAddAnnotation(){
        title.val('');
        text.val('');
        title.parent().removeClass('error');
        text.parent().removeClass('error');
        if(image != null){
            image.imgAreaSelect({hide: true});
        }
    }
    function clearAddSection(){
        sectiontitle.val('');
        sectionpage.val('');
        sectiontitle.parent().removeClass('error');
        sectionpage.parent().removeClass('error');
        sectionpage.parent().find('.fieldErrorBox').html('');
    }

    add_container.find('form').submit(function(){return false;});
    add_button.click(function(e){
        var titleval = title.val();
        var textval = text.val();
        var error = false;
        if(!titleval){
            title.parent().addClass('error');
            error = true;
        }else{
            title.parent().removeClass('error');
        }
        if(!textval){
            text.parent().addClass('error');
            error = true;
        }else{
            text.parent().removeClass('error');
        }
        if(SELECTION == null){
            alert("You must drag and select a part of the image for the annotation.");
            error = true;
        }
        if(error){
            return false;
        }
        $.ajax({
            url: baseUrl + '/@@documentviewer-annotate',
            type: 'POST',
            data: {
                'action': 'addannotation',
                'title': titleval,
                'content': textval,
                'coord': SELECTION.y1 + ',' + SELECTION.x2 + ',' + SELECTION.y2 + ',' + SELECTION.x1,
                'page': pselect.val(),
                '_authenticator': $('[name="_authenticator"]').val()
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
                clearAddAnnotation();
            }
        });
        return false;
    });

    $('#annotations').on('click', 'a.remove', function(){
        var link = $(this);
        var id = parseInt($(this).attr('rel'));
        var page = parseInt($(this).attr('page'));
        $.ajax({
            url: baseUrl + '/@@documentviewer-annotate',
            type: 'POST',
            data: {
                'action': 'removeannotation',
                'id': id,
                'page': page,
                '_authenticator': $('[name="_authenticator"]').val()
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
        $(this).parent().hide();
        annotations.empty();
        clearAddAnnotation();
        clearAddSection();
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
        sections.append('<li>' + title +' '+window.dv_translated_label_for_page+' '+ page +
                '&nbsp;(<a href="#" rel="' + page + '" title="' + title +
                    '" class="remove">'+window.dv_translated_label_remove+'</a>)</li>');
    }

    add_section_button.click(function(){
        var titleval = sectiontitle.val();
        var pageval = sectionpage.val();
        var error = false;
        if(!titleval){
            sectiontitle.parent().addClass('error');
            error = true;
        }else{
            sectiontitle.parent().removeClass('error');
        }
        if(!pageval){
            sectionpage.parent().addClass('error');
            error = true;
        }else if(isNaN(pageval)){
            sectionpage.parent().addClass('error');
            error = true;
            sectionpage.parent().find('.fieldErrorBox').html("Must be a valid page number.");
        }else{
            pageval = parseInt(pageval);
            if(pageval <= 0 || pageval > window.documentData.pages){
                sectionpage.parent().addClass('error');
                error = true;
                sectionpage.parent().find('.fieldErrorBox').html("Number not a valid document page.");
            }else{
                sectionpage.parent().removeClass('error');
                sectionpage.parent().find('.fieldErrorBox').html('');
            }
        }
        if(error){
            return false;
        }
        $.ajax({
            url: baseUrl + '/@@documentviewer-annotate',
            type: 'POST',
            data: {
                'action': 'addsection',
                'title': titleval,
                'page': pageval,
                '_authenticator': $('[name="_authenticator"]').val()
            },
            dataType: 'json',
            success: function(data){
                addToSectionList(titleval, pageval);
                window.documentData.sections.push({
                    title: titleval,
                    page: pageval});
                reloadDV();
                clearAddSection();
            }
        });
        return false;
    });

    $('#sections').on('click', 'a.remove', function(){
        var link = $(this);
        var titleval = $(this).attr('title');
        var pageval = parseInt($(this).attr('rel'));
        $.ajax({
            url: baseUrl + '/@@documentviewer-annotate',
            type: 'POST',
            data: {
                'action': 'removesection',
                'title': titleval,
                'page': pageval,
                '_authenticator': $('[name="_authenticator"]').val()
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
        sections_container.show();
        return false;
    });

});
})(jQuery);