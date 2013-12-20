var view=null;var library_router=null;var responses=[];define(["galaxy.modal","galaxy.masthead","utils/galaxy.utils","libs/toastr"],function(j,k,g,m){var e=Backbone.Model.extend({urlRoot:"/api/libraries"});var n=Backbone.Collection.extend({url:"/api/libraries",model:e});var h=Backbone.Model.extend({urlRoot:"/api/libraries/datasets"});var c=Backbone.Collection.extend({model:h});var d=Backbone.Model.extend({defaults:{folder:new c(),full_path:"unknown",urlRoot:"/api/folders/",id:"unknown"},parse:function(q){this.full_path=q[0].full_path;this.get("folder").reset(q[1].folder_contents);return q}});var b=Backbone.Model.extend({urlRoot:"/api/histories/"});var i=Backbone.Model.extend({url:"/api/histories/"});var o=Backbone.Collection.extend({url:"/api/histories",model:i});var p=Backbone.Router.extend({routes:{"":"libraries","folders/:id":"folder_content","folders/:folder_id/download/:format":"download"}});var l=Backbone.View.extend({el:"#center",progress:0,progressStep:1,lastSelectedHistory:"",modal:null,folders:null,initialize:function(){this.folders=[];this.queue=jQuery.Deferred();this.queue.resolve()},templateFolder:function(){var q=[];q.push('<div id="library_container" style="width: 90%; margin: auto; margin-top: 2em; ">');q.push('<h3>New Data Libraries. This is work in progress. Report problems & ideas to <a href="mailto:marten@bx.psu.edu?Subject=DataLibraries_Feedback" target="_blank">Marten</a>.</h3>');q.push('<div id="library_folder_toolbar" >');q.push('   <button title="Create New Folder" id="toolbtn_create_folder" class="btn btn-primary" type="button"><span class="fa fa-plus"></span> <span class="fa fa-folder-close"></span> folder</button>');q.push('   <button id="toolbtn_bulk_import" class="btn btn-primary" style="display: none; margin-left: 0.5em;" type="button"><span class="fa fa-external-link"></span> to history</button>');q.push('   <div id="toolbtn_dl" class="btn-group" style="margin-left: 0.5em; display: none; ">');q.push('       <button id="drop_toggle" type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown">');q.push('       <span class="fa fa-download"></span> download <span class="caret"></span>');q.push("       </button>");q.push('       <ul class="dropdown-menu" role="menu">');q.push('          <li><a href="#/folders/<%= id %>/download/tgz">.tar.gz</a></li>');q.push('          <li><a href="#/folders/<%= id %>/download/tbz">.tar.bz</a></li>');q.push('          <li><a href="#/folders/<%= id %>/download/zip">.zip</a></li>');q.push("       </ul>");q.push("   </div>");q.push("</div>");q.push('<div class="library_breadcrumb">');q.push('<a title="Return to the list of libraries" href="#">Libraries</a> <b>|</b> ');q.push("<% _.each(path, function(path_item) { %>");q.push("<% if (path_item[0] != id) { %>");q.push('<a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> <b>|</b> ');q.push("<% } else { %>");q.push('<span title="You are in this folder"><%- path_item[1] %></span>');q.push("<% } %>");q.push("<% }); %>");q.push("</div>");q.push('<table id="folder_table" class="table table-condensed">');q.push("   <thead>");q.push('       <th style="text-align: center; width: 20px; "><input id="select-all-checkboxes" style="margin: 0;" type="checkbox"></th>');q.push('       <th class="button_heading">view</th>');q.push("       <th>name</th>");q.push("       <th>data type</th>");q.push("       <th>size</th>");q.push("       <th>date</th>");q.push("   </thead>");q.push("   <tbody>");q.push("       <td></td>");q.push('       <td><button title="Go to parent folder" type="button" data-id="<%- upper_folder_id %>" class="btn_open_folder btn btn-default btn-xs">');q.push('       <span class="fa fa-arrow-up"></span> .. go up</td>');q.push("       <td></td>");q.push("       <td></td>");q.push("       <td></td>");q.push("       <td></td>");q.push("       </tr>");q.push("       <% _.each(items, function(content_item) { %>");q.push('       <tr class="folder_row light" id="<%- content_item.id %>">');q.push('           <% if (content_item.get("type") === "folder") { %>');q.push("               <td></td>");q.push('               <td><button title="Open this folder" type="button" data-id="<%- content_item.id %>" class="btn_open_folder btn btn-default btn-xs">');q.push('               <span class="fa fa-folder-open"></span> browse</td>');q.push('               <td><%- content_item.get("name") %>');q.push('           <% if (content_item.get("item_count") === 0) { %>');q.push('           <span class="muted">(empty folder)</span>');q.push("           <% } %>");q.push("           </td>");q.push("           <td>folder</td>");q.push('           <td><%= _.escape(content_item.get("item_count")) %> item(s)</td>');q.push("           <% } else {  %>");q.push('           <td style="text-align: center; "><input style="margin: 0;" type="checkbox"></td>');q.push("       <td>");q.push('       <button title="See details of this dataset" type="button" class="library-dataset btn btn-default btn-xs">');q.push('       <span class="fa fa-eye"></span> details');q.push("       </button>");q.push("       </td>");q.push('           <td><%- content_item.get("name") %></td>');q.push('           <td><%= _.escape(content_item.get("data_type")) %></td>');q.push('           <td><%= _.escape(content_item.get("readable_size")) %></td>');q.push("           <% } %>  ");q.push('           <td><%= _.escape(content_item.get("time_updated")) %></td>');q.push("       </tr>");q.push("       <% }); %>");q.push("       ");q.push("   </tbody>");q.push("</table>");q.push("</div>");return q.join("")},templateDatasetModal:function(){var q=[];q.push('<div id="dataset_info_modal">');q.push('   <table class="table table-striped table-condensed">');q.push("       <tr>");q.push('           <th scope="row" id="id_row" data-id="<%= _.escape(item.get("ldda_id")) %>">Name</th>');q.push('           <td><%= _.escape(item.get("name")) %></td>');q.push("       </tr>");q.push("       <tr>");q.push('           <th scope="row">Data type</th>');q.push('           <td><%= _.escape(item.get("data_type")) %></td>');q.push("       </tr>");q.push("       <tr>");q.push('           <th scope="row">Genome build</th>');q.push('           <td><%= _.escape(item.get("genome_build")) %></td>');q.push("       </tr>");q.push('           <th scope="row">Size</th>');q.push("           <td><%= _.escape(size) %></td>");q.push("       </tr>");q.push("       <tr>");q.push('           <th scope="row">Date uploaded</th>');q.push('           <td><%= _.escape(item.get("date_uploaded")) %></td>');q.push("       </tr>");q.push("       <tr>");q.push('           <th scope="row">Uploaded by</th>');q.push('           <td><%= _.escape(item.get("uploaded_by")) %></td>');q.push("       </tr>");q.push('           <tr scope="row">');q.push('           <th scope="row">Data Lines</th>');q.push('           <td scope="row"><%= _.escape(item.get("metadata_data_lines")) %></td>');q.push("       </tr>");q.push('       <th scope="row">Comment Lines</th>');q.push('           <% if (item.get("metadata_comment_lines") === "") { %>');q.push('               <td scope="row"><%= _.escape(item.get("metadata_comment_lines")) %></td>');q.push("           <% } else { %>");q.push('               <td scope="row">unknown</td>');q.push("           <% } %>");q.push("       </tr>");q.push("       <tr>");q.push('           <th scope="row">Number of Columns</th>');q.push('           <td scope="row"><%= _.escape(item.get("metadata_columns")) %></td>');q.push("       </tr>");q.push("       <tr>");q.push('           <th scope="row">Column Types</th>');q.push('           <td scope="row"><%= _.escape(item.get("metadata_column_types")) %></td>');q.push("       </tr>");q.push("       <tr>");q.push('           <th scope="row">Miscellaneous information</th>');q.push('           <td scope="row"><%= _.escape(item.get("misc_blurb")) %></td>');q.push("       </tr>");q.push("   </table>");q.push('   <pre class="peek">');q.push("   </pre>");q.push("</div>");return q.join("")},templateHistorySelectInModal:function(){var q=[];q.push('<span id="history_modal_combo" style="width:90%; margin-left: 1em; margin-right: 1em; ">');q.push("Select history: ");q.push('<select id="dataset_import_single" name="dataset_import_single" style="width:50%; margin-bottom: 1em; "> ');q.push("   <% _.each(histories, function(history) { %>");q.push('       <option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>');q.push("   <% }); %>");q.push("</select>");q.push("</span>");return q.join("")},templateBulkImportInModal:function(){var q=[];q.push('<span id="history_modal_combo_bulk" style="width:90%; margin-left: 1em; margin-right: 1em; ">');q.push("Select history: ");q.push('<select id="dataset_import_bulk" name="dataset_import_bulk" style="width:50%; margin-bottom: 1em; "> ');q.push("   <% _.each(histories, function(history) { %>");q.push('       <option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>');q.push("   <% }); %>");q.push("</select>");q.push("</span>");return q.join("")},size_to_string:function(q){var r="";if(q>=100000000000){q=q/100000000000;r="TB"}else{if(q>=100000000){q=q/100000000;r="GB"}else{if(q>=100000){q=q/100000;r="MB"}else{if(q>=100){q=q/100;r="KB"}else{q=q*10;r="b"}}}}return(Math.round(q)/10)+r},events:{"click #select-all-checkboxes":"selectAll","click .folder_row":"selectClickedRow","click #toolbtn_bulk_import":"modalBulkImport","click #toolbtn_dl":"bulkDownload","click .library-dataset":"showDatasetDetails","click #toolbtn_create_folder":"createFolderModal","click .btn_open_folder":"navigateToFolder"},render:function(q){$("#center").css("overflow","auto");view=this;var s=this;var r=new d({id:q.id});r.url=r.attributes.urlRoot+q.id+"/contents";r.fetch({success:function(t){for(var v=0;v<r.attributes.folder.models.length;v++){var u=r.attributes.folder.models[v];if(u.get("type")==="file"){u.set("readable_size",s.size_to_string(u.get("file_size")))}}var x=r.full_path;var y;if(x.length===1){y=0}else{y=x[x.length-2][0]}var w=_.template(s.templateFolder(),{path:r.full_path,items:r.attributes.folder.models,id:q.id,upper_folder_id:y});s.$el.html(w)}})},navigateToFolder:function(r){var q=$(r.target).attr("data-id");if(typeof q==="undefined"){return false}else{if(q==="0"){library_router.navigate("#",{trigger:true,replace:true})}else{library_router.navigate("folders/"+q,{trigger:true,replace:true})}}},showDatasetDetails:function(t){t.preventDefault();var u=$(t.target).parent().parent().attr("id");var s=new h();var r=new o();s.id=u;var q=this;s.fetch({success:function(v){r.fetch({success:function(w){q.renderModalAfterFetch(v,w)}})}})},renderModalAfterFetch:function(v,s){var t=this.size_to_string(v.get("file_size"));var u=_.template(this.templateDatasetModal(),{item:v,size:t});this.modal=null;var r=this;this.modal=new j.GalaxyModal({title:"Dataset Details",body:u,buttons:{Import:function(){r.importCurrentIntoHistory()},Download:function(){r.downloadCurrent()},Close:function(){r.modal.hide();$(".modal").remove();r.modal=null}}});this.modal.bindEvents(event,this);$(".peek").html(v.get("peek"));var q=_.template(this.templateHistorySelectInModal(),{histories:s.models});$(this.modal.elMain).find(".buttons").prepend(q);if(r.lastSelectedHistory.length>0){$(this.modal.elMain).find("#dataset_import_single").val(r.lastSelectedHistory)}this.modal.show()},downloadCurrent:function(){this.modal.disableButton("Import");this.modal.disableButton("Download");var q=[];q.push($("#id_row").attr("data-id"));var r="/api/libraries/datasets/download/uncompressed";var s={ldda_ids:q};folderContentView.processDownload(r,s);this.modal.enableButton("Import");this.modal.enableButton("Download")},importCurrentIntoHistory:function(){this.modal.disableButton("Import");this.modal.disableButton("Download");var s=$(this.modal.elMain).find("select[name=dataset_import_single] option:selected").val();this.lastSelectedHistory=s;var q=$("#id_row").attr("data-id");var t=new b();var r=this;t.url=t.urlRoot+s+"/contents";t.save({content:q,source:"library"},{success:function(){m.success("Dataset imported");r.modal.enableButton("Import");r.modal.enableButton("Download")},error:function(){m.error("An error occured! Dataset not imported. Please try again.");r.modal.enableButton("Import");r.modal.enableButton("Download")}})},selectAll:function(r){var q=r.target.checked;that=this;$(":checkbox").each(function(){this.checked=q;$row=$(this.parentElement.parentElement);(q)?that.makeDarkRow($row):that.makeWhiteRow($row)});this.checkTools()},selectClickedRow:function(r){var t="";var q;var s;if(r.target.localName==="input"){t=r.target;q=$(r.target.parentElement.parentElement);s="input"}else{if(r.target.localName==="td"){t=$("#"+r.target.parentElement.id).find(":checkbox")[0];q=$(r.target.parentElement);s="td"}}if(t===""){r.stopPropagation();return}if(t.checked){if(s==="td"){t.checked="";this.makeWhiteRow(q)}else{if(s==="input"){this.makeDarkRow(q)}}}else{if(s==="td"){t.checked="selected";this.makeDarkRow(q)}else{if(s==="input"){this.makeWhiteRow(q)}}}this.checkTools()},makeDarkRow:function(q){q.removeClass("light");q.find("a").removeClass("light");q.addClass("dark");q.find("a").addClass("dark")},makeWhiteRow:function(q){q.removeClass("dark");q.find("a").removeClass("dark");q.addClass("light");q.find("a").addClass("light")},checkTools:function(){var q=$("#folder_table").find(":checked");if(q.length>0){$("#toolbtn_bulk_import").show();$("#toolbtn_dl").show()}else{$("#toolbtn_bulk_import").hide();$("#toolbtn_dl").hide()}},modalBulkImport:function(){var r=this;var q=new o();q.fetch({success:function(s){var t=_.template(r.templateBulkImportInModal(),{histories:s.models});r.modal=new j.GalaxyModal({title:"Import into History",body:t,buttons:{Import:function(){r.importAllIntoHistory()},Close:function(){r.modal.hide();$(".modal").remove();r.modal=null}}});r.modal.show()}})},importAllIntoHistory:function(){this.modal.disableButton("Import");var s=$("select[name=dataset_import_bulk] option:selected").val();var w=$("select[name=dataset_import_bulk] option:selected").text();var y=[];$("#folder_table").find(":checked").each(function(){if(this.parentElement.parentElement.id!=""){y.push(this.parentElement.parentElement.id)}});var x=_.template(this.templateProgressBar(),{history_name:w});$(this.modal.elMain).find(".modal-body").html(x);var t=100/y.length;this.initProgress(t);var q=[];for(var r=y.length-1;r>=0;r--){library_dataset_id=y[r];var u=new b();var v=this;u.url=u.urlRoot+s+"/contents";u.content=library_dataset_id;u.source="library";q.push(u)}this.chainCall(q)},chainCall:function(r){var q=this;var s=r.pop();if(typeof s==="undefined"){m.success("All datasets imported");this.modal.hide();q.modal.enableButton("Import");return}var t=$.when(s.save({content:s.content,source:s.source})).done(function(u){q.updateProgress();responses.push(u);q.chainCall(r)})},initProgress:function(q){this.progress=0;this.progressStep=q},updateProgress:function(){this.progress+=this.progressStep;$(".progress-bar").width(Math.round(this.progress)+"%");txt_representation=Math.round(this.progress)+"% Complete";$(".completion_span").text(txt_representation)},templateProgressBar:function(){var q=[];q.push('<div class="import_text">');q.push("Importing selected datasets to history <b><%= _.escape(history_name) %></b>");q.push("</div>");q.push('<div class="progress">');q.push('   <div class="progress-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width: 00%;">');q.push('       <span class="completion_span">0% Complete</span>');q.push("   </div>");q.push("</div>");q.push("");return q.join("")},download:function(q,u){var s=[];$("#folder_table").find(":checked").each(function(){if(this.parentElement.parentElement.id!=""){s.push(this.parentElement.parentElement.id)}});var r="/api/libraries/datasets/download/"+u;var t={ldda_ids:s};this.processDownload(r,t,"get")},processDownload:function(r,s,t){if(r&&s){s=typeof s=="string"?s:$.param(s);var q="";$.each(s.split("&"),function(){var u=this.split("=");q+='<input type="hidden" name="'+u[0]+'" value="'+u[1]+'" />'});$('<form action="'+r+'" method="'+(t||"post")+'">'+q+"</form>").appendTo("body").submit().remove();m.info("Your download will begin soon")}},createFolderModal:function(){m.info("This will create folder...in the future")}});var a=Backbone.View.extend({el:"#center",events:{"click #create_new_library_btn":"show_library_modal"},initialize:function(){},template_library_list:function(){tmpl_array=[];tmpl_array.push('<div id="library_container" style="width: 90%; margin: auto; margin-top: 2em; overflow: auto !important; ">');tmpl_array.push("");tmpl_array.push('<h3>New Data Libraries. This is work in progress. Report problems & ideas to <a href="mailto:marten@bx.psu.edu?Subject=DataLibraries_Feedback" target="_blank">Marten</a>.</h3>');tmpl_array.push('<a href="" id="create_new_library_btn" class="btn btn-primary file ">New Library</a>');tmpl_array.push('<table class="table table-condensed">');tmpl_array.push("   <thead>");tmpl_array.push('     <th class="button_heading"></th>');tmpl_array.push("     <th>name</th>");tmpl_array.push("     <th>description</th>");tmpl_array.push("     <th>synopsis</th> ");tmpl_array.push("     <th>model type</th> ");tmpl_array.push("   </thead>");tmpl_array.push("   <tbody>");tmpl_array.push("       <% _.each(libraries, function(library) { %>");tmpl_array.push("           <tr>");tmpl_array.push('               <td><button title="Open this library" type="button" data-id="<%- library.get("root_folder_id") %>" class="btn_open_folder btn btn-default btn-xs">');tmpl_array.push('               <span class="fa fa-folder-open"></span> browse</td>');tmpl_array.push('               <td><%- library.get("name") %></td>');tmpl_array.push('               <td><%= _.escape(library.get("description")) %></td>');tmpl_array.push('               <td><%= _.escape(library.get("synopsis")) %></td>');tmpl_array.push('               <td><%= _.escape(library.get("model_class")) %></td>');tmpl_array.push("           </tr>");tmpl_array.push("       <% }); %>");tmpl_array.push("   </tbody>");tmpl_array.push("</table>");tmpl_array.push("</div>");return tmpl_array.join("")},render:function(){$("#center").css("overflow","auto");var q=this;libraries=new n();libraries.fetch({success:function(r){var s=_.template(q.template_library_list(),{libraries:r.models});q.$el.html(s)},error:function(s,r){if(r.statusCode().status===403){m.error("Please log in first. Redirecting to login page in 3s.");setTimeout(q.redirectToLogin,3000)}else{m.error("An error occured. Please try again.")}}})},redirectToHome:function(){window.location="../"},redirectToLogin:function(){window.location="/user/login"},modal:null,show_library_modal:function(r){r.preventDefault();r.stopPropagation();var q=this;this.modal=new j.GalaxyModal({title:"Create New Library",body:this.template_new_library(),buttons:{Create:function(){q.create_new_library_event()},Close:function(){q.modal.hide()}}});this.modal.show()},create_new_library_event:function(){var s=this.serialize_new_library();if(this.validate_new_library(s)){var r=new e();var q=this;r.save(s,{success:function(t){q.modal.hide();q.clear_library_modal();q.render();m.success("Library created")},error:function(){m.error("An error occured :(")}})}else{m.error("Library's name is missing")}return false},clear_library_modal:function(){$("input[name='Name']").val("");$("input[name='Description']").val("");$("input[name='Synopsis']").val("")},serialize_new_library:function(){return{name:$("input[name='Name']").val(),description:$("input[name='Description']").val(),synopsis:$("input[name='Synopsis']").val()}},validate_new_library:function(q){return q.name!==""},template_new_library:function(){tmpl_array=[];tmpl_array.push('<div id="new_library_modal">');tmpl_array.push("<form>");tmpl_array.push('<input type="text" name="Name" value="" placeholder="Name">');tmpl_array.push('<input type="text" name="Description" value="" placeholder="Description">');tmpl_array.push('<input type="text" name="Synopsis" value="" placeholder="Synopsis">');tmpl_array.push("</form>");tmpl_array.push("</div>");return tmpl_array.join("")}});var f=Backbone.View.extend({folderContentView:null,galaxyLibraryview:null,initialize:function(){folderContentView=new l();galaxyLibraryview=new a();library_router=new p();library_router.on("route:libraries",function(){galaxyLibraryview.render()});library_router.on("route:folder_content",function(q){folderContentView.render({id:q})});library_router.on("route:download",function(q,r){if($("#center").find(":checked").length===0){library_router.navigate("folders/"+q,{trigger:true,replace:true})}else{folderContentView.download(q,r);library_router.navigate("folders/"+q,{trigger:false,replace:true})}});Backbone.history.start();return this}});return{GalaxyApp:f}});