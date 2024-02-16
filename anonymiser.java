import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class anonymiser {

    // STRING ARRAY-KS
    public static String[] splitStringIntoArray(String input) {
        // Split the input string into an array of words
        String[] words = input.split("\\s+");
        return words;
    }

    
    public static String processText(String[] input) {
        
        
        for (int i = 1; i < input.length; i++) {
            // Nimi?

            if(input[i].matches(".*[A-Z].*")){
                if(input[i-1].endsWith(".")) {

                }
            }
        }
        return "info";
    }

    // ESIMESED SÕNAD LAUSES
    public static String[] extractFirstWords(String text) {
        List<String> firstWordsList = new ArrayList<>();

        // Define a regex pattern to match sentence boundaries
        Pattern pattern = Pattern.compile("(?<=\\.\\s|\\?\\s|!\\s|^)[A-Z0-9][^.!?]*");

        // Create a matcher to find matches in the text
        Matcher matcher = pattern.matcher(text);

        // Iterate over matches to extract the first word of each sentence
        while (matcher.find()) {
            // Get the matched sentence
            String sentence = matcher.group();
            // Split the sentence into words and extract the first word
            String[] words = sentence.split("\\s+");
            // Add the first word to the list
            firstWordsList.add(words[0]);
        }

        // Convert the list to an array
        String[] firstWordsArray = firstWordsList.toArray(new String[0]);

        return firstWordsArray;
    }

    private static final String NAME_REGEX = "\\b[A-Z][a-z]*\\b";
    private static final String ADDRESS_REGEX = "\\b\\d+\\s+([a-zA-Z]+|[a-zA-Z]+\\s[a-zA-Z]+)\\b";

    public static String[] identifyPersonalInfo(String input) {
        // Create a StringBuilder to dynamically store the matched strings
        StringBuilder infoBuilder = new StringBuilder();

        // Compile regex patterns
        Pattern namePattern = Pattern.compile(NAME_REGEX);
        Pattern addressPattern = Pattern.compile(ADDRESS_REGEX);

        // Match names
        Matcher nameMatcher = namePattern.matcher(input);
        while (nameMatcher.find()) {
            String match = nameMatcher.group();
            infoBuilder.append(match).append(", ");
        }

        // Match addresses
        Matcher addressMatcher = addressPattern.matcher(input);
        while (addressMatcher.find()) {
            String match = addressMatcher.group();
            infoBuilder.append(match).append(", ");
        }

        // Convert the StringBuilder to a string and split it into an array by comma and space
        String[] info = infoBuilder.toString().split(", ");
        
        return info;
    }

    public static void main(String[] args) {
        String text = "Kiisu nimega Mirjam Miisu elab aadressil Valge 16, Tallinn. Mirjamile ei meeldi oma naaber Juhan, kes mjäugub liiga valjult. Mirjam on 4 aastane isikukoodiga 62001240838. Mirjamiga saab ühendust võtta numbril +37259108902 või mirjam.miisu@gmail.com. 12 kiisut suri korea sõjas! Miks küll nii pidi juhtuma? Miks?! Mirjam sündis 24.07.2002.";
        //String[] personalInfo = identifyPersonalInfo(text);

        String[] textArray = splitStringIntoArray(text);

        String[] firstWords = extractFirstWords(text);
        
        for (String info : firstWords) {
            System.out.println(info);
        }
        // Print the identified personal information
        /* for (String info : personalInfo) {
            System.out.println(info);
        }
        
        System.out.println("-----------------");

        for (String info : textArray) {
            System.out.println(info);
        } */
    }
}