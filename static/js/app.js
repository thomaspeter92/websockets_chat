
// Support TLS-specific URLs, when appropriate.
if (window.location.protocol == "https:") {
    var ws_scheme = "wss://";
  } else {
    var ws_scheme = "ws://"
  };
  
  const $ = (ele) => document.querySelector(ele)
  
  var inbox = new ReconnectingWebSocket(ws_scheme + location.host + "/receive");
  var outbox = new ReconnectingWebSocket(ws_scheme + location.host + "/submit");
  
  inbox.onmessage = function(message) {
    var data = JSON.parse(message.data);
    let msg = document.createElement('div')
    msg.classList.add('message')
    msg.innerHTML = `<div class='message-title'>${data.handle}</div><div class='message-text'>${data.text}</div>`;
    $("#chat-text").appendChild(msg)
    $("#chat-text").scrollTo(0, $("#chat-text").scrollHeight)
  };
  
  inbox.onclose = function(){
      console.log('inbox closed');
      this.inbox = new WebSocket(inbox.url);
  
  };
  
  outbox.onclose = function(){
      console.log('outbox closed');
      this.outbox = new WebSocket(outbox.url);
  };
  

//THORTTLING MESSAGES ON THE FRONT END.
// any function can be passed into the throttler, along with any time.
  const throttleFunction = (func, wait) => {
      let callFunc = true
      return function(...args) {
          var now = Date.now()
          if (callFunc) {
              func(...args)
              callFunc = false
              setTimeout(() =>  callFunc = true, wait)
          }else {
                  console.log('too soon')
          }
      }
  }
  
  const sendMessage = (event) => {
      event.preventDefault();
      var handle = $("#input-handle").value;
      var text   = $("#input-text").value;
      outbox.send(JSON.stringify({ handle: handle, text: text }));
      $("#input-text").value = "";
  }
  //pass the send message function into the throttle function here and assign to throttleSendMessage which will be called on the submit event.
  const throttleSendMessage = throttleFunction(sendMessage, 1000)
  
  $("#input-form").addEventListener("submit", (e) => {
      e.preventDefault();
      throttleSendMessage(e)
  })
  