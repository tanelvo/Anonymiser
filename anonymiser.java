import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class anonymiser {

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
        String text = "Kiisu nimega Mirjam Miisu elab aadressil Valge 16, Tallinn. Mirjamile ei meeldi oma naaber Juhan, kes mjäugub liiga valjult. Mirjam on 4 aastane isikukoodiga 62001240838. Mirjamiga saab ühendust võtta numbril +37259108902 või mirjam.miisu@gmail.com.";
        String[] personalInfo = identifyPersonalInfo(text);
        
        // Print the identified personal information
        for (String info : personalInfo) {
            System.out.println(info);
        }
    }
}