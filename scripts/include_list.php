<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
</style>

<?php
error_reporting(E_ALL);
ini_set('display_errors',1);

$filename = './scripts/labels.txt';
$eachlines = file($filename, FILE_IGNORE_NEW_LINES);

?>

<div class="customlabels smaller">
<br>
</div>
<body style="height: 90%;">
  <p>Warning!<br>If this list contains ANY species, the system will ONLY recognize those species. Keep this list EMPTY unless you are ONLY interested in detecting specific species.</p>
<div class="customlabels2 column1">
<form action="" method="GET" id="add">
  <h2>All Species Labels</h2>
  <input autocomplete="off" size="18" type="text" placeholder="Search Species..." id="species_searchterm" name="species_searchterm">
  <select name="species[]" id="species" multiple size="25">
      <?php   
        foreach($eachlines as $lines){echo 
    "<option value=\"".$lines."\">$lines</option>";}
       ?>
  </select>
  <input type="hidden" name="add" value="add">
</form>
<div class="customlabels2 smaller">
  <button type="submit" name="view" value="Included" form="add">>>ADD>></button>
</div>
</div>

<div class="customlabels2 column4">
  <table><td>
  <button type="submit" name="view" value="Included" form="add">>>ADD>></button>
  <br><br>
  <button type="submit" name="view" value="Included" form="del">REMOVE</button>
  </td></table>
</div>

<div class="customlabels2 column3">
<form action="" method="GET" id="del">
  <h2>Custom Species List</h2>
  <select name="species[]" id="value2" multiple size="25">
  <option disabled value="base">Please Select</option>
      <?php
        $filename = './scripts/include_species_list.txt';
        $eachlines = file($filename, FILE_IGNORE_NEW_LINES);
        foreach($eachlines as $lines){echo 
    "<option value=\"".$lines."\">$lines</option>";}
      ?>
  </select>
  <input type="hidden" name="del" value="del">
</form>
<div class="customlabels2 smaller">
  <button type="submit" name="view" value="Included" form="del">REMOVE</button>
</div>
</div>

<script>
    // Store the original list of options in a variable
    var originalOptions = {};

    document.getElementById("add").addEventListener("submit", function(event) {
      var speciesSelect = document.getElementById("species");
      if (speciesSelect.selectedIndex < 0) {
        alert("Please click the species you want to add.");
        document.querySelector('.views').style.opacity = 1;
        event.preventDefault();
      }
    });

    var search_term = document.querySelector("input#species_searchterm");
    search_term.addEventListener("keyup", function() {
      filterOptions("species");
    });

    // Function to filter options in a select element
    function filterOptions(id) {
      var input = document.getElementById(id + "_searchterm");
      var filter = input.value.toUpperCase();
      var select = document.getElementById(id);
      var options = select.getElementsByTagName("option");

      // If the original list of options for this select element hasn't been stored yet, store it
      if (!originalOptions[id]) {
        originalOptions[id] = Array.from(options).map(option => option.value);
      }

      // Clear the select element
      while (select.firstChild) {
        select.removeChild(select.firstChild);
      }

      // Populate the select element with the filtered labels
      originalOptions[id].forEach(label => {
        if (label.toUpperCase().indexOf(filter) > -1) {
          let option = document.createElement('option');
          option.value = label;
          option.text = label;
          select.appendChild(option);
        }
      });
    }
</script>
