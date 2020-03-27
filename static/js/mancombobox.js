$(function(){
    $.widget("ui.autocomplete", $.ui.autocomplete, {
        _renderMenu: function(ul, items){
            let that = this;
            let ctx = ul[0].ctx;
            $.each(items, function(index, item){
                that._renderItemData(ul, item);
            });
            $(ul).find("li:odd").addClass("odd");

            if(ctx){
                let l_item = $( "<li>" ).attr("data-value","-");
                l_item.height('20px');
                l_item.width('60px');
                let next_btn = $("<a>").addClass("custom-combobox-pagination").css("position", "relative").css("float", "right")
                    .attr("tabIndex", -1)
                    .attr("title","下一页").tooltip().appendTo(l_item).button({
                    icons: {
                      primary: "ui-icon-triangle-1-s"
                    },
                    text: false
                  }).on("click", function(event) {
                      ul[0].page = ctx.page + 1;
                      that.element.autocomplete("search", that.element.val());
                      event.stopPropagation();
                });
                let pre_btn = $("<a>").addClass("custom-combobox-pagination").css("position", "relative").css("float", "left")
                    .attr("tabIndex", -1)
                    .attr("title","上一页").tooltip().appendTo(l_item).button({
                    icons: {
                      primary: "ui-icon-triangle-1-n"
                    },
                    text: false
                  }).on("click", function(event) {
                      ul[0].page = ctx.page - 1;
                      that.element.autocomplete("search", that.element.val());
                    event.stopPropagation();
                });
                l_item.appendTo(ul);
                if(!ctx.has_next){
                    next_btn.button("disable");
                }
                if(!ctx.has_pre){
                    pre_btn.button("disable");
                }
            }

          }
    });
    $.widget( "custom.combobox", {
        _create: function() {
            this.wrapper = $("<span>").addClass("custom-combobox").insertAfter(this.element);
            this.element.hide();
            this._createAutocomplete();
            this._createShowAllButton();
            return this;
        },
        _createAutocomplete: function() {
            let that = this;
            let selected = this.element.children(":selected"),value = selected.val() ? selected.text() : "";
            this.input = $("<input>").appendTo(this.wrapper).val(value).attr("title","")
              .addClass( "custom-combobox-input ui-widget ui-widget-content ui-state-default ui-corner-left" )
              .autocomplete({
                  appendTo:this.options.parent,
                delay: 0,
                minLength: 0,
                source: $.proxy(this,"_source"),
                  change:function(event, ui){
                      console.log("change ui:", ui);
                      that.wrapper.find('input[name=sel]').val(ui.item.option.fuzzy_id);
                      event.stopPropagation();
                      return false;
                  }
              }).tooltip({
                classes: {
                  "ui-tooltip": "ui-state-highlight"
                }
              });
            this._on( this.input, {
              autocompleteselect: function( event, ui ) {
                ui.item.option.selected = true;
                this._trigger( "select", event, {
                  item: ui.item.option
                });
              },
              autocompletechange: "_removeIfInvalid"
            });
        },
        _createShowAllButton: function() {
            let input = this.input,wasOpen = false;

            $("<a>").attr("tabIndex", -1).attr("title","Show All Items").tooltip().appendTo( this.wrapper )
              .button({
                icons: {
                  primary: "ui-icon-triangle-1-s"
                },
                text: false
              }).removeClass( "ui-corner-all" ).addClass( "custom-combobox-toggle ui-corner-right" )
              .on("mousedown", function() {
                wasOpen = input.autocomplete("widget").is(":visible");
              }).on("click", function() {
                input.trigger("focus");
                // Close if already visible
                if ( wasOpen ) {
                  return;
                }
                // Pass empty string as value to search for, displaying all results
                input.autocomplete("search", "");
              });
            $("<input>").attr("name", "sel").attr("tabIndex", -1).attr("type","hidden").appendTo( this.wrapper )
            // let widget_ui = input.autocomplete("widget");
            // let options = this.options;
            // if(options.parent){
            //     if(widget_ui.parent() != options.parent){
            //         widget_ui.appendTo(options.parent);
            //     }
            // }
            // console.log("widget_ui:", widget_ui, ",options:", options);
        },
        _source: function( request, response ) {
            // console.log("_source request:", request,",res:", response);
            let matcher = new RegExp( $.ui.autocomplete.escapeRegex(request.term), "i" );
            // let item_list = this.element.children("option").map(function() {
            //   let text = $(this).text();
            //   // console.log("source map val:",this.value, ",term:",!request.term);
            //   if (this.value && ( !request.term || matcher.test(text) )){
            //       return {
            //           label: text,
            //           value: text,
            //           option: this
            //       };
            //   }
            // });
            let widget_ui = this.input.autocomplete("widget");
            if(this.options.src){
                if(!widget_ui[0].page){
                    widget_ui[0].page = 1;
                }
                request.page = widget_ui[0].page;
                this.options.src(request, (res)=>{
                    console.log("res:", res);
                    widget_ui[0].ctx = {"has_next": res.hasnext, "has_pre": res.haspre, "page":res.page};
                    widget_ui[0].page = 1;
                    items = $(res.datas).map(function(){
                        // if(!request.term || matcher.test(this.filename)){
                        //
                        // }
                        return {
                              label: this.name+'['+this.fuzzy_id+']',
                              value: this.name,
                              option: this
                          };
                    });
                    response(items);
                });
            }

            // console.log("item_list:", item_list);
            // response(item_list);
        },
        _removeIfInvalid: function( event, ui ) {
            // Selected an item, nothing to do
            if ( ui.item ) {
              return;
            }
            // Search for a match (case-insensitive)
            let value = this.input.val(),valueLowerCase = value.toLowerCase(),valid = false;
            this.element.children( "option" ).each(function() {
              if ( $( this ).text().toLowerCase() === valueLowerCase ) {
                this.selected = valid = true;
                return false;
              }
            });
            // Found a match, nothing to do
            if ( valid ) {
              return;
            }
            // Remove invalid value
            this.input.val("").attr( "title", value + " didn't match any item" ).tooltip( "open" );
            this.element.val( "" );
            this._delay(function() {
              this.input.tooltip( "close" ).attr( "title", "" );
            }, 2500 );
            this.input.autocomplete( "instance" ).term = "";
        },
        _destroy: function() {
            this.wrapper.remove();
            this.element.show();
        }
    });
})
