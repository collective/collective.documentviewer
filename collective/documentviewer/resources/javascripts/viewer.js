(function($){
$(document).ready(function(){

$('.close-fullscreen').on('click', function(){
  if(window.opener){
    window.close();
    window.opener.location = jQuery('base').attr('href') + '/view#bypass-fullscreen';
    window.opener.location.reload();
  }else{
    window.location = jQuery('base').attr('href') + '/view#bypass-fullscreen';
    window.location.reload();
  }
  return false;
});


$('#errorMsg a').click(function(){
  $('#errorMsg dd').slideDown();
  return false;
})

});
})(jQuery);
