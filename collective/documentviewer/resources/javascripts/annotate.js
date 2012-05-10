SELECTION = null;

(function($){
$(document).ready(function(){

    $('#add-annotation').click(function(){
        var page = parseInt(window.currentDocument.elements.currentPage.html());
        var image = $('.DV-page-' + page + ' img:first');
        var container = $('<div id="annotate-container" />');
        var image = image.clone();
        container.append(image);
        $('body').append(container);
        var width = image.width(), height = image.height();
        image.imgAreaSelect({
            handles: true,
            onSelectEnd: function (img, selection) {
                SELECTION = selection;
            },
            x1: width/4, y1: height/4, x2: width/2, y2: height/2
        });

        var controls = $('<div id="annotate-controls" />');
        controls.append('<label>Title</label>');
        var title = $('<input type="text" />');
        controls.append(title);
        controls.append('<label>Text</label>');
        var text = $('<textarea></textarea>');
        controls.append(text);
        var add = $('<button class="add">Annotate</button>');
        add.click(function(){
            $.ajax({
                url: $('base').attr('href') + '/@@documentviewer-annotate',
                type: 'POST',
                data: {
                    'action': 'add',
                    'title': title.val(),
                    'content': text.val(),
                    'coord': SELECTION.y1 + ',' + SELECTION.x2 + ',' + SELECTION.y2 + ',' + SELECTION.x1,
                    'page': page
                },
                success: function(){
                    window.location.reload();
                }
            });
            return false;
        });
        controls.append(add);
        var close = $('<button id="close">Close Annotations</button>');
        close.click(function(){
            image.imgAreaSelect({remove: true});
            controls.remove();
            container.remove();
            return false;
        });
        controls.append(close);
        $('body').append(controls);
        return false;
    });

    $('#remove-annotations').click(function(){
        var page = parseInt(window.currentDocument.elements.currentPage.html());
        var image = $('.DV-page-' + page + ' img:first');
        var container = $('<div id="annotate-remove" />');
        var ann = $('<ul />');
        $.each(window.documentData.annotations, function(){
            if(this.page == page){
                ann.append('<li>' + this.title + 
                    '(<a href="#" rel="' + this.id + '" class="remove">Remove</a>)</li>');
            }
        });
        ann.find('.remove').click(function(){
            var link = $(this);
            $.ajax({
                url: $('base').attr('href') + '/@@documentviewer-annotate',
                type: 'POST',
                data: {
                    'action': 'remove',
                    'id': $(this).attr('rel'),
                    'page': page
                },
                success: function(){
                    link.parent().remove();
                }
            });
            return false;
        });
        container.append(ann);
        var close = $('<button id="close">Close</button>');
        close.click(function(){
            container.remove();
            window.location.reload();
            return false;
        });
        container.append(close);
        $('body').append(container);
        return false;
    });

});
})(jQuery);